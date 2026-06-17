ORDERS_HEADERS = [
    "OrderID", "TelegramID", "CustomerName", "Telephone",
    "Items", "Total", "Allergies",
    "SpecialInstructions", "DeliveryAddress",
    "DeliveryTime", "Status", "Language",
    "CreatedAt", "UpdatedAt"
]

MENU_HEADERS = [
    "ItemID", "Name_EN", "Name_ZH", "Name_JP",
    "Category", "Price", "Allergens", "Available"
]

CUSTOMERS_HEADERS = [
    "CustomerID", "TelegramID", "FirstName", "LastName",
    "Phone", "Address", "TotalOrders", "LastOrderDate",
    "FirstSeen"
]

FEEDBACK_HEADERS = [
    "FeedbackID", "OrderID", "TelegramID",
    "CustomerName", "Rating", "Comment",
    "Date"
]

SHEET_DEFINITIONS = {
    "Orders": {
        "headers": ORDERS_HEADERS,
        "tab_index": 0,
    },
    "Menu": {
        "headers": MENU_HEADERS,
        "tab_index": 1,
    },
    "Customers": {
        "headers": CUSTOMERS_HEADERS,
        "tab_index": 2,
    },
    "Feedback": {
        "headers": FEEDBACK_HEADERS,
        "tab_index": 3,
    },
}
