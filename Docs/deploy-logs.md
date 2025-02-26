2025-02-26 00:46:55,602 - bot - ERROR - Error in message processing: 'HybridMemoryManager' object has no attribute 'get_history_context'

2025-02-26 00:46:55,602 - bot - DEBUG - [DEBUG][Chat -1002157344870] Processing error: 'HybridMemoryManager' object has no attribute 'get_history_context'

2025-02-26 00:46:55,602 - bot - DEBUG - [DEBUG][Chat -1002157344870] Attempting fallback

2025-02-26 00:46:55,622 - httpcore.connection - DEBUG - connect_tcp.started host='api.openai.com' port=443 local_address=None timeout=5.0 socket_options=None

2025-02-26 00:46:55,637 - httpcore.connection - DEBUG - connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x7fcba73d8dd0>

2025-02-26 00:46:55,637 - httpcore.connection - DEBUG - start_tls.started ssl_context=<ssl.SSLContext object at 0x7fcba787f1d0> server_hostname='api.openai.com' timeout=5.0

2025-02-26 00:46:55,650 - httpcore.connection - DEBUG - start_tls.complete return_value=<httpcore._backends.sync.SyncStream object at 0x7fcba75bbf90>

2025-02-26 00:46:55,650 - httpcore.http11 - DEBUG - send_request_headers.started request=<Request [b'POST']>

2025-02-26 00:46:55,651 - httpcore.http11 - DEBUG - send_request_headers.complete

2025-02-26 00:46:55,651 - httpcore.http11 - DEBUG - send_request_body.started request=<Request [b'POST']>

2025-02-26 00:46:55,651 - httpcore.http11 - DEBUG - send_request_body.complete

2025-02-26 00:46:55,651 - httpcore.http11 - DEBUG - receive_response_headers.started request=<Request [b'POST']>

2025-02-26 00:46:56,142 - httpcore.http11 - DEBUG - receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Wed, 26 Feb 2025 00:46:56 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'access-control-expose-headers', b'X-Request-ID'), (b'openai-organization', b'user-jrobrdv8bldfakdoyxdsiky9'), (b'openai-processing-ms', b'347'), (b'openai-version', b'2020-10-01'), (b'x-ratelimit-limit-requests', b'10000'), (b'x-ratelimit-limit-tokens', b'200000'), (b'x-ratelimit-remaining-requests', b'9999'), (b'x-ratelimit-remaining-tokens', b'196981'), (b'x-ratelimit-reset-requests', b'8.64s'), (b'x-ratelimit-reset-tokens', b'905ms'), (b'x-request-id', b'req_e686fb045f86202cb66d6e3ac15338e9'), (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'), (b'CF-Cache-Status', b'DYNAMIC'), (b'Set-Cookie', b'__cf_bm=0UU1eCEIXYaY4f4vNo4.HzGk9H50sARw.4r1eW8EqqQ-1740530816-1.0.1.1-75RmbdnKPUKIiymVLwjEvDra.Ul0msqal5V1uVmHOThgPzcSyYa50oIXyp.z.lFVl8ZDX9Dt.o3pGD66wkMbiw; path=/; expires=Wed, 26-Feb-25 01:16:56 GMT; domain=.api.openai.com; HttpOnly; Secure; SameSite=None'), (b'X-Content-Type-Options', b'nosniff'), (b'Set-Cookie', b'_cfuvid=FBsRUVAbNczxlz5HlfIlyLog0MKedk8r3kZGGGwHBjw-1740530816139-0.0.1.1-604800000; path=/; domain=.api.openai.com; HttpOnly; Secure; SameSite=None'), (b'Server', b'cloudflare'), (b'CF-RAY', b'917bebbdd9fb6456-SJC'), (b'Content-Encoding', b'gzip'), (b'alt-svc', b'h3=":443"; ma=86400')])

2025-02-26 00:46:56,143 - httpx - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

2025-02-26 00:46:56,144 - httpcore.http11 - DEBUG - receive_response_body.started request=<Request [b'POST']>

2025-02-26 00:46:56,147 - httpcore.http11 - DEBUG - receive_response_body.complete

2025-02-26 00:46:56,148 - httpcore.http11 - DEBUG - response_closed.started

2025-02-26 00:46:56,148 - httpcore.http11 - DEBUG - response_closed.complete

