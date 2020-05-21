# encoding=utf8

import logging
import sys

import order_data
import data_export

TEST_ORDER_FILENAME = 'orders_export_0418_food_grocery'
TEST_DAY_OF_WEEK = 'Saturday'
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def main():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG)
    logging.info("Start")

    order_filename, weekday = get_args()
    city_branch_mapping = order_data.get_city_branch_mapping(weekday)
    pickup_locations = order_data.get_pickup_locations()
    orders, line_items_by_branch, item_summaries_by_branch, fieldnames = order_data.process_orders(order_filename, city_branch_mapping, pickup_locations)
    orders_by_branch = order_data.group_orders_by_branch(orders)
    delivery_locations = order_data.get_delivery_locations(orders)

    order_output_dir = data_export.set_up_output_dir(order_filename)

    data_export.output_order_summary(orders, order_filename, order_output_dir)
    data_export.output_delivery_locations(delivery_locations, order_filename, order_output_dir)
    data_export.output_line_items_by_branch(line_items_by_branch, fieldnames, weekday,
                                            order_filename, order_output_dir)
    data_export.output_line_items_for_branches(line_items_by_branch, fieldnames,
                                               order_filename, order_output_dir)
    data_export.output_item_summary_by_branch(item_summaries_by_branch,
                                              order_filename, order_output_dir)
    logging.info("Output files saved in %s", order_output_dir)

    data_export.generate_items_pdf(item_summaries_by_branch, order_output_dir)
    data_export.generate_orders_pdf(orders_by_branch, order_output_dir)

def get_args():
    try:
        order_filename = sys.argv[1]
    except IndexError:
        order_filename = TEST_ORDER_FILENAME
        logging.error("Error in arguments")

    try:
        weekday = WEEKDAYS[int(sys.argv[2])-1]
    except IndexError:
        weekday = TEST_DAY_OF_WEEK

    return order_filename, weekday

if __name__ == '__main__':
    main()
