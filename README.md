# Order Report Generator

Order Report Generator summarizes online orders and generates reports for Shopify. It takes a CSV order file and organizes it by product, order, and customer address. Currently, it is primarily tailored to use cases for restaurants.

## Features
* Generate order summary, order shipping labels, item summary report, consolidated delivery locations.
* Customize delivery area based on day of week.
* Allocate orders to different branch locations based on customer address.
* Set customer pickup locations based on shipping method.

## Dependencies

* jinja2
* pdfkit
* wkhtmltopdf

## Command
```
python report_generator.py <filename> <weekday>
```
where `weekday` is an integer from 1 to 7, for Monday (1) to Sunday (7).

### Example

Given an order file named `orders_export.csv`, run this command to generate reports based on Sunday's delivery area:

```
python report_generator.py orders_export 7
```

## Order data format

Currently, the script expects input order data in the format seen in the exported order CSV files from Shopify. See this help page for the data structure: https://help.shopify.com/en/manual/orders/export-orders#order-export-csv-structure.

## Configurations

* **pickup_locations.csv**: mapping between shipping method and address of pickup location; used to generate delivery location summary.
* **weekly_schedule.csv**: weekly schedule of delivery areas defined at the shipping city level.

## Output

### CSV files
* **order_summary.csv**: key order information, including order number, shipping address, branch allocation, item counts.
* **delivery_locations.csv**: orders grouped by delivery locations, in cases of multiple orders from same customer or orders at central pickup locations; can be used for route planning.
* **line_items_\<branch\>.csv**: line items for each branch
* **item_summaries_\<branch\>.csv**: item counts for each branch

Errors while processing orders
* **not_scheduled**: orders not in the delivery area of the day
* **unknown_city**: shipping city is not defined in weekly_schedule.tsv config file

### PDF files
* **reports/\<branch\>-items.pdf**: item counts with comments from each order
* **reports/\<branch\>-orders.pdf**: order info in the form of shipping labels

## Execution environments

The script can be executed locally on a desktop, or deployed to cloud services such as AWS, with the script running in a Lambda function, saving output files to a S3 bucket, and invoked via an API Gateway endpoint.
