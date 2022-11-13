Hello {{user.first_name}}
You have new messages in these discussions

{% for chat in chats %}
    {{chat.content_object.title}}
{% endfor %}
