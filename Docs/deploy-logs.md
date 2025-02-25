2025-02-25 22:48:41,926 - bot - INFO - Processing update through application...

2025-02-25 22:48:42,403 - telegram.ext.ExtBot - DEBUG - Message(channel_chat_created=False, chat=Chat(first_name='Naz', id=308526396, type=<ChatType.PRIVATE>, username='nm_2719'), date=datetime.datetime(2025, 2, 25, 22, 48, 42, tzinfo=datetime.timezone.utc), delete_chat_photo=False, from_user=User(first_name='Dildong', id=8050570051, is_bot=True, username='Dildong_bot'), group_chat_created=False, message_id=230, supergroup_chat_created=False, text="Current Bot Rules:\n\n1. Be helpful, concise, and friendly. (Priority: 10)\n2. Respond in the same language as the user's message. (Priority: 9)\n3. If you learn someone's name, use it in future responses. (Priority: 8)\n4. Keep track of important information shared in conversation. (Priority: 7)\n5. Be respectful and maintain a positive tone. (Priority: 6)")

2025-02-25 22:48:41,926 - bot - INFO - Calling process_update...

2025-02-25 22:48:41,926 - bot - INFO - Processing /rules command from chat_id 308526396

2025-02-25 22:48:41,926 - utils.database - DEBUG - Using file-based fallback for temporary account

2025-02-25 22:48:41,927 - utils.rule_manager - ERROR - Cannot get rules: Supabase client is not initialized

2025-02-25 22:48:41,927 - bot - INFO - No rules found for account 2. Creating default rules.

2025-02-25 22:48:41,927 - utils.rule_manager - ERROR - Cannot create default rules: Supabase client is not initialized

2025-02-25 22:48:41,927 - utils.rule_manager - INFO - Using file-based fallback for default rules

2025-02-25 22:48:41,928 - utils.rule_manager - INFO - Default rules created in file storage for account 2

2025-02-25 22:48:41,928 - utils.rule_manager - ERROR - Cannot get rules: Supabase client is not initialized

2025-02-25 22:48:41,928 - bot - INFO - Created 5 default rules for account 2

2025-02-25 22:48:41,928 - telegram.ext.ExtBot - DEBUG - Entering: send_message

2025-02-25 22:48:41,929 - httpcore.connection - DEBUG - close.started

2025-02-25 22:48:41,929 - httpcore.connection - DEBUG - close.complete

2025-02-25 22:48:41,929 - httpcore.connection - DEBUG - connect_tcp.started host='api.telegram.org' port=443 local_address=None timeout=5.0 socket_options=None

2025-02-25 22:48:42,079 - httpcore.connection - DEBUG - connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x7f2370a99790>

2025-02-25 22:48:42,079 - httpcore.connection - DEBUG - start_tls.started ssl_context=<ssl.SSLContext object at 0x7f2370b4ec30> server_hostname='api.telegram.org' timeout=5.0

2025-02-25 22:48:42,229 - httpcore.connection - DEBUG - start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x7f2370a991d0>

2025-02-25 22:48:42,229 - httpcore.http11 - DEBUG - send_request_headers.started request=<Request [b'POST']>