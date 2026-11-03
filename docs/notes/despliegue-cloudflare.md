# Despliegue en Cloudflare Pages

Estado (03-11-2026, 00:35 UTC): **corte cerrado**. `29n.info` se sirve desde
Cloudflare Pages a través de la zona de Cloudflare, con certificado propio y HTTP/3.
Vercel ya no tiene el dominio: queda solo `encuestas29n.vercel.app` como espejo.

Cronología del corte, por si vuelve a hacer falta:

| Hora UTC | Hecho |
|---|---|
| 23:34 | Zona `29n.info` creada en Cloudflare (pending) |
| 23:36 | Proyecto Pages `29n` y primer despliegue (221 ficheros) |
| — | Cambio de nameservers en DonDominio (Chema) |
| 23:48 | Zona `active` tras `activation_check` (`Zone verified!`) |
| 23:48–00:27 | Sin certificado de borde: el proxy no puede servir HTTPS. Se devuelven los registros a Vercel sin proxy para no dejar el dominio caído |
| 00:27 | Universal SSL emitido (Google Trust Services, CN=29n.info) |
| 00:29 | Registros a `29n.pages.dev` proxiados y HTTPS forzado |
| 00:31 | Verificado por Cloudflare: 15 rutas 200, 404 correcto, `www` 301 al apex, contenido idéntico al build |
| 00:40 | Dominios retirados de Vercel |

**Lección**: el Universal SSL de una zona nueva puede tardar 40 minutos. No se puede
comprobar por API si el token no tiene permiso de certificados; la prueba fiable es
`openssl s_client -servername <dominio>` contra las IPs anycast de la zona. Conviene
hacer esa prueba **antes** de mover el DNS, o aceptar una ventana sin HTTPS.

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

- `CNAME 29n.info → 29n.pages.dev`, proxiado (CNAME flattening en el apex).
- `CNAME www.29n.info → 29n.pages.dev`, proxiado.
- Page Rule `www.29n.info/*` → 301 a `https://29n.info/$1`, para no servir dos copias.
  Por eso Cloudflare marca el dominio `www` del proyecto Pages como `deactivated`:
  el que responde es la regla de la zona, antes de llegar a Pages.
- `always_use_https` y `automatic_https_rewrites` en `on`.

Cabeceras de caché en `web/public/_headers`: `/_astro/*` un año `immutable` (los
nombres llevan hash del contenido), `/og/*` un día, y `nosniff` +
`strict-origin-when-cross-origin` para todo.

## Certificado

Universal SSL de Cloudflare, emitido por Google Trust Services, válido hasta
2027-02-01. La sonda `~/.hermes/scripts/29n_espera_cert.sh` sirve para diagnosticar
(zona activa sin certificado) más que para este dominio ya resuelto.

No hay MX ni TXT en el dominio: no hay correo que se pueda romper al mover la zona.

## Paridad verificada (antes de tocar DNS)

Los 221 ficheros de `web/dist` se hashearon contra `https://29n.pages.dev`:
**221 idénticos, 0 distintos, 0 fallos**. El HTML es byte a byte el mismo que el
build local.

## Rollback

1. En Cloudflare, cambiar el apex a `A 76.76.21.21` y `www` a `cname.vercel-dns.com`,
   ambos **sin proxy** (así el TLS lo termina Vercel y no depende de nada nuestro).
2. Reañadir `29n.info` al proyecto Vercel (`POST /v9/projects/encuestas29n/domains`).
3. Verificar `200` y cabecera `x-vercel-id`.

El proyecto Vercel `encuestas29n` sigue existiendo con su integración de Git, así que
cada push sigue generando un despliegue en `encuestas29n.vercel.app`: es un espejo
gratis y el camino de vuelta si algo se tuerce.

## Pendiente

- Nada bloqueante. El despliegue lo hace el cron diario después de pushear.
- Opcional: conectar el repo a Pages (Pages → Connect to Git) para build en
  Cloudflare; entonces el script local deja de ser necesario.
- Opcional: borrar el proyecto Vercel y su espejo cuando el corte lleve unos días
  estable.
