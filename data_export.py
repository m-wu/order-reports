import csv
import logging
import os
import shutil

import jinja2
import pdfkit

CSV_EXT = '.csv'
OUTPUT_DIR = 'output'
REPORTS_DIR = 'reports'

GENERATE_HTML = False

ORDERS_TEMPLATE_FILE = "templates/orders-template.html"
ORDERS_TEMPLATE_CSS_FILE = "templates/orders-style-prefix.css"

ITEMS_TEMPLATE_FILE = "templates/items-template.html"
ITEMS_TEMPLATE_CSS_FILE = "templates/items-style.css"

def set_up_output_dir(order_filename):
    order_output_dir = os.path.join(OUTPUT_DIR, order_filename)
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    if not os.path.exists(order_output_dir):
        os.mkdir(order_output_dir)
    report_dir = os.path.join(order_output_dir, REPORTS_DIR)
    if not os.path.exists(report_dir):
        os.mkdir(report_dir)
    shutil.copy(order_filename+CSV_EXT, os.path.join(order_output_dir, order_filename+CSV_EXT))
    return order_output_dir

def output_order_summary(orders, order_filename, order_output_dir):
    output_file_name = order_filename+'_order_summary.csv'
    output_file_path = os.path.join(order_output_dir, output_file_name)
    with open(output_file_path, 'w') as output_file:
        headers = ['order_number', 'fulfillment_status', 'shipping_street', 'shipping_city',
                   'shipping_name', 'shipping_phone', 'branch', 'shipping_method',
                   'item_count', 'food_item_count']
        output_writer = csv.DictWriter(output_file, headers, extrasaction='ignore')
        output_writer.writeheader()
        order_values = orders.values()
        order_values = sorted(order_values, key=lambda order: order['order_number'])
        for order in order_values:
            output_writer.writerow(order)

def output_item_summary_by_branch(item_summaries_by_branch, order_filename, order_output_dir):
    for branch in item_summaries_by_branch:
        item_summary = item_summaries_by_branch[branch]
        output_file_name = "{}_item_summaries_{}{}".format(order_filename, branch, CSV_EXT)
        output_file_path = os.path.join(order_output_dir, output_file_name)

        if item_summary:
            with open(output_file_path, 'w') as output_file:
                headers = ['count', 'short_name']
                output_writer = csv.DictWriter(output_file, headers, extrasaction='ignore')
                output_writer.writeheader()
                sorted_item_summary = sorted(item_summary, key=lambda order: order['count'], reverse=True)
                for item in sorted_item_summary:
                    output_writer.writerow(item)
        else:
            if os.path.exists(output_file_path):
                logging.info("Removing file: %s", output_file_path)
                os.remove(output_file_path)

def output_delivery_locations(delivery_locations, order_filename, order_output_dir):
    output_file_name = order_filename+'_delivery_locations.csv'
    output_file_path = os.path.join(order_output_dir, output_file_name)
    with open(output_file_path, 'w') as output_file:
        headers = ['location_id', 'branch', 'shipping_street', 'shipping_city',
                   'order_count', 'order_numbers']
        output_writer = csv.DictWriter(output_file, headers, extrasaction='ignore')
        output_writer.writeheader()
        delivery_locations = sorted(delivery_locations, key=lambda order: order['location_id'])
        for order in delivery_locations:
            output_writer.writerow(order)

def output_line_items_by_branch(line_items_by_branch, fieldnames, weekday, 
                                order_filename, order_output_dir):
    for branch in line_items_by_branch:
        line_items = line_items_by_branch[branch]
        output_file_name = "{}_line_items_{}{}".format(order_filename, branch, CSV_EXT)
        output_file_path = os.path.join(order_output_dir, output_file_name)
        if line_items:
            if branch == 'unknown_city':
                logging.warning("Check %s for unknown shipping city.", output_file_path)
            elif branch == 'not_scheduled':
                logging.warning("Check %s for orders outside %s's delivery areas.",
                                output_file_path, weekday)
            with open(output_file_path, 'w') as output_file:
                output_writer = csv.DictWriter(output_file, fieldnames, extrasaction='ignore')
                output_writer.writeheader()
                for line_item in line_items:
                    output_writer.writerow(line_item)
        else:
            if os.path.exists(output_file_path):
                logging.info("Removing file: %s", output_file_path)
                os.remove(output_file_path)

def output_line_items_for_branches(line_items_by_branch, fieldnames,
                                   order_filename, order_output_dir):
    output_file_name = "{}_line_items_all_branches{}".format(order_filename, CSV_EXT)
    output_file_path = os.path.join(order_output_dir, output_file_name)
    with open(output_file_path, 'w') as output_file:
        output_writer = csv.DictWriter(output_file, fieldnames, extrasaction='ignore')
        output_writer.writeheader()
        for branch in line_items_by_branch:
            for line_item in line_items_by_branch[branch]:
                output_writer.writerow(line_item)

def generate_items_pdf(item_summaries_by_branch, order_output_dir):
    for branch in item_summaries_by_branch:
        items = item_summaries_by_branch[branch]

        filename = branch + '-items'
        output_html_file_path = os.path.join(order_output_dir, REPORTS_DIR, filename + '.html')
        output_pdf_file_path = os.path.join(order_output_dir, REPORTS_DIR, filename + '.pdf')

        if items:
            template_loader = jinja2.FileSystemLoader(searchpath="./")
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template(ITEMS_TEMPLATE_FILE)

            sorted_items = sorted(items, key=lambda i: i['count'], reverse=True)
            output = template.render(items=sorted_items, branch=branch)

            if GENERATE_HTML:
                with open(output_html_file_path, 'w') as html_file:
                    html_file.write(output)

            css_path = os.path.join(os.getcwd(), ITEMS_TEMPLATE_CSS_FILE)
            pdfkit.from_string(output, output_pdf_file_path, css=css_path)
        else:
            if os.path.exists(output_html_file_path):
                logging.info("Removing file: %s", output_html_file_path)
                os.remove(output_html_file_path)
            if os.path.exists(output_pdf_file_path):
                logging.info("Removing file: %s", output_pdf_file_path)
                os.remove(output_pdf_file_path)

def generate_orders_pdf(orders_by_branch, order_output_dir):
    for branch in orders_by_branch:
        orders = orders_by_branch[branch]

        filename = branch + '-orders'
        output_html_file_path = os.path.join(order_output_dir, REPORTS_DIR, filename + '.html')
        output_pdf_file_path = os.path.join(order_output_dir, REPORTS_DIR, filename + '.pdf')

        if orders:
            template_loader = jinja2.FileSystemLoader(searchpath="./")
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template(ORDERS_TEMPLATE_FILE)
            output = template.render(orders=orders, branch=branch)

            if GENERATE_HTML:
                with open(output_html_file_path, 'w') as html_file:
                    html_file.write(output)

            css_path = os.path.join(os.getcwd(), ORDERS_TEMPLATE_CSS_FILE)
            pdfkit.from_string(output, output_pdf_file_path, css=css_path)
        else:
            if os.path.exists(output_html_file_path):
                logging.info("Removing file: %s", output_html_file_path)
                os.remove(output_html_file_path)
            if os.path.exists(output_pdf_file_path):
                logging.info("Removing file: %s", output_pdf_file_path)
                os.remove(output_pdf_file_path)
