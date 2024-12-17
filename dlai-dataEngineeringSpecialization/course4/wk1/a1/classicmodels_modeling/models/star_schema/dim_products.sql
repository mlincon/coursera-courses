SELECT
    {{ dbt_utils.generate_surrogate_key(['productCode']) }} AS product_key, --noqa: TMP, PRS, LT02
    productName AS product_name,
    products.productLine AS product_line,
    productScale AS product_scale,
    productVendor AS product_vendor,
    productDescription AS product_description,
    textDescription AS product_line_description
FROM {{ var("source_schema") }}.products
INNER JOIN {{ var("source_schema") }}.productlines
    ON products.productLine = productlines.productLine --noqa: CP02
