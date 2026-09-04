import httpx


def async_client(*, proxies=None, **kwargs):
    if proxies:
        if isinstance(proxies, str):
            kwargs["proxy"] = proxies
        elif isinstance(proxies, dict):
            all_proxy = proxies.get("all://")
            if all_proxy:
                kwargs["proxy"] = all_proxy
            else:
                mounts = {
                    scheme: httpx.AsyncHTTPTransport(proxy=proxy)
                    for scheme, proxy in proxies.items()
                    if proxy
                }
                if mounts:
                    kwargs["mounts"] = mounts

    return httpx.AsyncClient(**kwargs)
