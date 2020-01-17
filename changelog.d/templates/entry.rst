* {% if pr_ids is defined and pr_ids -%}
{% for pr in pr_ids -%}
`#{{ pr }} <{{ prs_url }}/{{ pr }}>`_{% if not loop.last %}, {% endif %}
{%- endfor %}: {% endif -%}
{{ message }}

