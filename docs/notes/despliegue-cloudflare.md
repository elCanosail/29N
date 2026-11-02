# Despliegue en Cloudflare Pages

Estado: **29n.info se sirve desde Cloudflare Pages** (proyecto `29n`). Vercel queda
como respaldo hasta que el cambio de nameservers esté propagado y verificado.

## Piezas

| Pieza | Valor |
|---|---|
| Proyecto Pages | `29n`, rama de producción `main` |
| URL estable | `https://29n.pages.dev` |
| Build | `cd web && npm ci && npm run build` → `web/dist` |
| Zona Cloudflare | `29n.info`, id `41a07711b55df24cd3c2c5b07bacc3be` |
| Nameservers asignados | `kiki.ns.cloudflare.com`, `marty.ns.cloudflare.com` |

## Desplegar

```bash
~/.hermes/scripts/29n_pages_deploy.sh            # build + deploy + comprobación
~/.hermes/scripts/29n_pages_deploy.sh --sin-build
```

El script corre **en esta máquina**, no en GitHub: el token de Cloudflare vive solo
aquí (`~/.hermes/secrets/cloudflare-token-yuj`, 0600) y no hay que meter un token de
cuenta en los secretos de un repositorio público. El cron diario de encuestas lo
llama después de pushear, así que una ingesta con datos nuevos se publica sola.

Alternativa si algún día se quiere build en Cloudflare: conectar el repo desde el
dashboard (Pages → Connect to Git). Entonces el script local deja de ser necesario.

## DNS

Registros creados en la zona nueva:

- `CNAME 29n.info → 29n.pages.dev`, proxiado (CNAME flattening en el apex).
- `CNAME www.29n.info → 29n.pages.dev`, proxiado.
- Page Rule `www.29n.info/*` → 301 a `https://29n.info/$1`, para no servir dos
  copias del sitio.

No hay MX ni TXT en el dominio: no hay correo que se pueda romper al mover la zona.

## Paridad verificada (antes de tocar DNS)

Los 221 ficheros de `web/dist` se hashearon contra `https://29n.pages.dev`:
**221 idénticos, 0 distintos, 0 fallos**. El HTML es byte a byte el mismo que el
build local.

## Rollback

1. En Cloudflare, devolver el `CNAME` del apex a `cname.vercel-dns.com` (proxiado).
2. Reañadir `29n.info` al proyecto Vercel (`POST /v10/projects/encuestas29n/domains`).
3. Verificar `200` y cabecera `x-vercel-id`.

El proyecto Vercel `encuestas29n` sigue existiendo y con sus dominios hasta que el
corte esté cerrado; no se borra nada mientras haya rollback posible.

## Pendiente

- **Cambio de nameservers en DonDominio** (ns1/ns2.dondominio.com →
  kiki/marty.ns.cloudflare.com). Sin eso, `29n.info` sigue resolviendo a Vercel y el
  dominio personalizado de Pages queda en `initializing`.
- Tras la propagación: comprobar `status: active` del dominio en Pages, retirar el
  dominio de Vercel y desconectar su integración de Git para que no dispare builds
  fallidos en cada push.
