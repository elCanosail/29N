# Despliegue en Cloudflare Pages

Estado (03-11-2026, 00:30 UTC): **la zona está activa en Cloudflare y el DNS ya es suyo,
pero el sitio todavía se sirve desde Vercel**. Cloudflare no ha emitido el certificado
de borde (Universal SSL) para `29n.info`, y sin él el proxy no puede servir HTTPS: el
handshake falla con `alert 40`. Para no dejar el dominio sin servicio, los registros
apuntan a Vercel **sin proxy** (HTTPS lo termina Vercel, con certificado válido) hasta
que exista el certificado de Cloudflare.

Comprobado con el registro: los nameservers delegados ya son `kiki` y `marty`
(RDAP de Identity Digital). La zona pasó a `active` con `activation_check`.

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

Estado actual (el seguro, mientras no haya certificado de borde):

- `A 29n.info → 76.76.21.21`, **sin proxy** (Vercel termina el TLS).
- `CNAME www.29n.info → cname.vercel-dns.com`, sin proxy.

Preparado para el corte final:

- Page Rule `www.29n.info/*` → 301 a `https://29n.info/$1` (solo actúa con proxy).

Los registros definitivos serán `CNAME 29n.info → 29n.pages.dev` y
`CNAME www.29n.info → 29n.pages.dev`, ambos proxiados, en cuanto exista el
certificado.

## Bloqueo abierto: certificado de borde

Cloudflare no ha emitido el Universal SSL de la zona. Comprobado por SNI contra las
IPs anycast de la zona (`104.21.61.212`, `172.67.215.101`) y contra otras IPs de
Cloudflare: `alert 40` en todas, tanto para `29n.info` como para `www.29n.info`.
El `activation_check` de la zona responde `Zone verified!` y la zona está `active`,
así que no es un problema de delegación.

El token de la cuenta no tiene permiso de certificados: `/ssl/*` y
`/ssl/certificate_packs` devuelven `403`/`Authentication error`, y
`PATCH /ssl/universal/settings` también. Hay que mirarlo en el panel
(SSL/TLS → Edge Certificates → Universal SSL) o esperar la emisión automática.

Sonda en marcha: `~/.hermes/scripts/29n_espera_cert.sh` consulta el certificado por
SNI cada 2 minutos y avisa en cuanto exista.

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
