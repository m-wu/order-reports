# encoding=utf8

import csv
import logging
import re
from collections import defaultdict

CSV_EXT = '.csv'

WEEKLY_SCHEDULE_FILENAME = 'config/weekly_schedule.tsv'
PICKUP_LOCATIONS_FILENAME = 'config/pickup_locations.csv'

BRANCHES = ['Edmonds', 'Redmond']
BRANCH_ERRORS = ['unknown_city', 'not_scheduled']

TIP_ITEM_NAME = '小费 Tip'
DELIVERY_FEE_ITEM_NAME = '运费补拍'
NON_FOOD_ITEMS = [TIP_ITEM_NAME, DELIVERY_FEE_ITEM_NAME]


def get_city_branch_mapping(weekday):
    logging.info("Applying schedule for %s", weekday)
    city_branch_mapping = {}
    with open(WEEKLY_SCHEDULE_FILENAME, 'r') as schedule_file:
        schedule_reader = csv.DictReader(schedule_file, delimiter='\t')
        for line in schedule_reader:
            city_branch_mapping[line['City'].upper()] = line[weekday]

    for branch in BRANCHES:
        cities = ([city for (city, branch_value) in city_branch_mapping.items()
                   if branch_value == branch])
        logging.info("%s: %s", branch, ", ".join(cities))

    return city_branch_mapping

def get_pickup_locations():
    pickup_locations = {}
    with open(PICKUP_LOCATIONS_FILENAME, 'r') as pickup_location_file:
        pickup_location_reader = csv.DictReader(pickup_location_file)
        for line in pickup_location_reader:
            pickup_locations[line['pickup_shipping_method']] = line
    return pickup_locations


def process_orders(order_filename, city_branch_mapping, pickup_locations):
    orders = {}
    fieldnames = []
    line_items_by_branch = {}
    items_by_name_branch = {}
    for branch in BRANCHES + BRANCH_ERRORS:
        line_items_by_branch[branch] = []
        items_by_name_branch[branch] = defaultdict(list)

    order_file_path = order_filename + CSV_EXT
    with open(order_file_path, 'r') as order_file:
        logging.info("Processing order file: %s", order_file_path)
        order_reader = csv.DictReader(order_file)
        fieldnames = order_reader.fieldnames
        for line in order_reader:
            line = {k:v.strip() for (k, v) in line.items()}

            order_number = line['Name']
            if order_number not in orders:
                order = {
                    'order_number': order_number,
                    'fulfillment_status': line['Fulfillment Status'],
                    'shipping_name': line['Shipping Name'],
                    'shipping_phone': format_phone_number(line['Shipping Phone']),
                    'notes': line['Notes'],
                    'taxes': float(line['Taxes']),
                    'shipping': float(line['Shipping']),
                    'total': float(line['Total']),
                    'line_items': []
                }
                order.update(get_order_branch(line, city_branch_mapping, pickup_locations))
                orders[order_number] = order

            line['is_food_item'] = line['Lineitem name'] not in NON_FOOD_ITEMS
            line['short_name'] = line['Lineitem name'].split()[0]
            line['total'] = float(line['Lineitem price']) * int(line['Lineitem quantity'])
            orders[order_number]['line_items'].append(line)

            branch = orders[order_number]['branch']
            line['Branch'] = branch
            line_items_by_branch[branch].append(line)

            items_by_name_branch[branch][line['Lineitem name']].append(line)

    orders = post_process_orders(orders)

    item_summaries_by_branch = summarize_items(items_by_name_branch, orders)

    fieldnames.insert(0, 'Branch')

    return orders, line_items_by_branch, item_summaries_by_branch, fieldnames

def group_orders_by_branch(orders):
    orders_by_branch = {}
    for branch in BRANCHES + BRANCH_ERRORS:
        orders_by_branch[branch] = []
    for order_number in orders:
        order = orders[order_number]
        orders_by_branch[order['branch']].append(order)
    return orders_by_branch

def summarize_items(items_by_name_branch, orders):
    item_summaries = {}
    for branch in items_by_name_branch:
        item_summaries[branch] = []
        for item_name in items_by_name_branch[branch]:
            if item_name in NON_FOOD_ITEMS:
                continue
            items = items_by_name_branch[branch][item_name]
            item_summary = {
                'item_name': item_name,
                'short_name': items[0]['short_name'],
                'count': sum([int(item['Lineitem quantity']) for item in items]),
                'notes': [
                    {
                        'note': orders[item['Name']]['notes'],
                        'quantity': item['Lineitem quantity'],
                        'order_number': item['Name']
                    }
                    for item in items if orders[item['Name']]['notes']]
            }
            item_summaries[branch].append(item_summary)

    return item_summaries


def format_phone_number(number): 
    if re.match("^\d{10}$", number):
        m = re.match("^(\d{3})(\d{3})(\d{4})$", number)
        return '({}) {}-{}'.format(*m.groups())
    if re.match("^'\+1\s", number):
        number = re.sub("^'\+1\s", '', number)
    if re.match("^(\d{3})\-(\d{3})\-(\d{4})$", number):
        m = re.match("^(\d{3})\-(\d{3})\-(\d{4})$", number)
        return '({}) {}-{}'.format(*m.groups())
    return number

def get_order_branch(line, city_branch_mapping, pickup_locations):
    branch = None
    pickup_point = None
    shipping_method = line['Shipping Method']
    for pickup_method in pickup_locations:
        if pickup_method in shipping_method:
            branch = pickup_locations[pickup_method]['branch']
            shipping_street = pickup_locations[pickup_method]['street_address']
            shipping_city = pickup_locations[pickup_method]['city']
            pickup_point = pickup_method
            break

    if not branch:
        shipping_street = line['Shipping Street']
        shipping_city = line['Shipping City']
        branch = city_branch_mapping.get(line['Shipping City'].upper(), 'unknown_city')
        if not branch:
            branch = 'not_scheduled'

    return {
        'branch': branch,
        'shipping_street': shipping_street,
        'shipping_city': shipping_city,
        'shipping_method': shipping_method,
        'pickup_point': pickup_point
    }

def post_process_orders(orders):
    for order_number in orders:
        line_items = orders[order_number]['line_items']
        food_line_items = [item for item in line_items if item['Lineitem name'] not in NON_FOOD_ITEMS]
        item_count = len(line_items)
        food_item_count = len(food_line_items)

        food_item_subtotal = sum([item['total'] for item in line_items if item['Lineitem name'] not in NON_FOOD_ITEMS])
        tip_total = sum([item['total'] for item in line_items if item['Lineitem name'] == TIP_ITEM_NAME])
        shipping_total = sum([item['total'] for item in line_items if item['Lineitem name'] == DELIVERY_FEE_ITEM_NAME])\
                         + orders[order_number]['shipping']
        tax_total = sum([float(item['Taxes']) for item in line_items if item['Taxes']])
        total = sum([float(item['Total']) for item in line_items if item['Total']])

        orders[order_number].update({
            'item_count': item_count,
            'food_item_count': food_item_count,
            'food_item_subtotal': round(food_item_subtotal, 2),
            'tip_total': tip_total,
            'shipping_total': shipping_total
        })
    return orders

def get_delivery_locations(orders):
    delivery_locations = []
    orders_by_shipping_address = defaultdict(list)
    for order in orders.values():
        if order['food_item_count'] == 0:
            continue
        full_address = ','.join([order['shipping_street'], order['shipping_city']])
        orders_by_shipping_address[full_address].append(order)

    for address_orders in orders_by_shipping_address.values():
        location_id = address_orders[0]['pickup_point'] if address_orders[0]['pickup_point'] else address_orders[0]['order_number']
        delivery_location = {
            'location_id': location_id,
            'order_count': len(address_orders),
            'order_numbers': [order['order_number'] for order in address_orders]
        }
        delivery_location.update(address_orders[0])
        delivery_locations.append(delivery_location)
    return delivery_locations
