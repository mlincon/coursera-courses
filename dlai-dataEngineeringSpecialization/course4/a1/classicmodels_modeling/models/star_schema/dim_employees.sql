SELECT
    {{ dbt_utils.generate_surrogate_key(['employeeNumber']) }} AS employee_key, --noqa: TMP, PRS, LT02
    lastName AS employee_last_name,
    firstName AS employee_first_name,
    jobTitle AS job_title,
    email AS email
FROM {{ var("source_schema") }}.employees
