# Public CA certificate for MAX Bot API

`russian-trusted-root-ca.crt` is a **public root certificate, not a private key**.
It is bundled so reviewers do not need an additional certificate mount.

- Source: https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt
- Official landing page: https://www.gosuslugi.ru/crt
- Download and fingerprint checked: 2026-11-08
- Subject: `Russian Trusted Root CA`
- Expires: 2032-02-27
- SHA-256: `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`

The image copies this file to `/opt/arena/russian-trusted-root-ca.crt`. Only the
bot's SSL context loads it, in addition to system roots. TLS verification stays
enabled; the certificate is not installed in the global trust store. An explicit
`MAX_CA_BUNDLE` overrides this extra bundled root (not system roots).

To verify a replacement before committing it:

```bash
openssl x509 -in docker/certs/russian-trusted-root-ca.crt -noout -subject -dates -fingerprint -sha256
```
