#!/usr/bin/env python
"""Register, list and delete webhooks.

Unzer notifies you with `{event, publicKey, retrieveUrl, paymentId}` and does **not**
sign the request. Verify it by checking the source IP against Unzer's allowlist and by
fetching the resource from `retrieveUrl` yourself -- never trust the notification body.
"""

from _common import build_client

from unzer.model import Events, Webhook

URL = "https://shop.example.com/unzer/webhook"


def main() -> None:
    client = build_client()

    print("registered webhooks:")
    for webhook in client.listWebhooks():
        events = ", ".join(str(event) for event in webhook.event)
        print(f"  {webhook.webhookId}  {events}  {webhook.url}")

    # One call can register several events; the API answers with one webhook each.
    created = client.createWebhook(Webhook(url=URL, event=[
        Events.CHARGE_SUCCEEDED,
        Events.CHARGE_FAILED,
        Events.PAYMENT_COMPLETED,
    ]))
    print(f"\ncreated {len(created)}:")
    for webhook in created:
        events = ", ".join(str(event) for event in webhook.event)
        print(f"  {webhook.webhookId}  {events}")

    # Only the URL can be changed afterwards -- the event is fixed.
    first = created[0]
    first.url = URL + "?v=2"
    print(f"\nupdated: {client.updateWebhook(first).url}")

    for webhook in created:
        print(f"deleted: {client.deleteWebhook(webhook)}")


if __name__ == "__main__":
    main()
