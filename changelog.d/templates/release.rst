
{{ release_version }} ({{ release_date }})  
{{ "-" * release_version|length }}---{{ "-" * release_date|length }}
{% if release_description %}
{{ release_description }}  
{% endif %}{% for group in entry_groups %}
{{ group.title }}  
{{ "~" * group.title|length }}
{% for entry in group.entries %}{{ entry }}{% endfor %}{% endfor %}
