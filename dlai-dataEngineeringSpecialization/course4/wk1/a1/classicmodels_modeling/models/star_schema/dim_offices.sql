SELECT
    {{ dbt_utils.generate_surrogate_key(['officeCode']) }} AS office_key, --noqa: TMP, PRS, LT02
    postalCode AS postal_code,
    city AS city,
    state AS state,
    country AS country,
    territory AS territory
FROM {{ var("source_schema") }}.offices
