SELECT
    {{ dbt_utils.generate_surrogate_key(['customerNumber']) }} AS customer_key, --noqa: TMP, PRS, LT02
    customerName AS customer_name,
    contactLastName AS customer_last_name,
    contactFirstName AS customer_first_name,
    phone AS phone,
    addressLine1 AS address_line_1,
    addressLine2 AS address_line_2,
    postalCode AS postal_code,
    city AS city,
    state AS state,
    country AS country,
    creditLimit AS credit_limit
FROM {{ var("source_schema") }}.customers
