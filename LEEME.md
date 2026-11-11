# Calendario en el fondo

Tu Google Calendar en el fondo de pantalla de Windows, en directo y con clics. La app lee tu calendario con permiso de **solo lectura** (no puede cambiar nada), comprueba si hay cambios cada 15 segundos y los muestra al momento. Pincha en un evento para resaltarlo y ver su descripción.

**Necesitas:** Windows, [Python 3.10 o superior](https://www.python.org/downloads/) y un programa de fondos animados: [Wallpaper Engine](https://www.wallpaperengine.io/) o [Lively Wallpaper](https://www.rocksdanister.com/lively/) (gratis, en Microsoft Store).

## 1. Crea tu acceso a Google (una vez, unos 10 minutos)

1. Entra en [console.cloud.google.com](https://console.cloud.google.com) y crea un proyecto, por ejemplo «Calendario fondo».
2. **APIs y servicios › Biblioteca**: busca *Google Calendar API* y pulsa **Habilitar**.
3. **Google Auth Platform › Comenzar**: nombre de la app «Calendario fondo», tu correo y audiencia **Externa** (con una cuenta de Gmail es la única opción).
4. Elige cómo dejar la app:
   - **Opción A, en pruebas (recomendada para empezar).** En **Audiencia › Usuarios de prueba**, añade tu correo de Gmail; sin esto, Google te bloquea al dar permiso. El permiso caduca cada 7 días y se renueva con un clic (paso 4 de esta guía).
   - **Opción B, publicada.** Sin caducidad semanal, pero Google pide una página de inicio y una política de privacidad. Haz un *fork* de este repositorio, activa GitHub Pages (*Settings › Pages*, rama `main`, carpeta `/docs`) y pon en **Marca**: dominio autorizado `TU-USUARIO.github.io`, página de inicio `https://TU-USUARIO.github.io/calendario-fondo/` y política `…/privacidad.html`. Después, en **Audiencia**, pulsa **Publicar aplicación**.
5. **Clientes › Crear cliente**, tipo **Aplicación de escritorio**. Deja abierta la ventana con el **ID de cliente** y el **secreto de cliente**: el instalador te los pedirá. Google solo enseña el secreto completo al crearlo.

## 2. Instala

Ejecuta `instalar.bat`:

1. Pega el ID y el secreto cuando te los pida (clic derecho para pegar).
2. Espera a que instale las dependencias (un par de minutos, puede no mostrar nada).
3. Se abrirá el navegador: elige tu cuenta y acepta. Google avisará de que la app «no está verificada»; es normal, porque es tuya: pulsa **Continuar**.

La app queda en marcha y arranca sola con Windows.

## 3. Ponlo como fondo

- **Wallpaper Engine:** abre el editor y arrastra `fondo_pantalla\calendario.html` sobre el botón de crear fondo. Guárdalo y aplícalo desde tu biblioteca.
- **Lively:** pulsa **+** (Añadir fondo) y elige el mismo archivo.

Ese archivo no contiene datos: espera a que la app esté en marcha y entonces muestra el calendario.

## 4. Día a día

- **Cambios:** lo que hagas en Google Calendar aparece en el fondo en unos segundos.
- **Permiso caducado** (opción A, cada 7 días): abajo a la izquierda aparece un aviso con el botón **Volver a conectar**. Púlsalo y acepta en el navegador. Mientras tanto se siguen viendo los últimos datos. `reconectar.bat` hace lo mismo.
- **Sin conexión:** se muestra la última copia con un aviso, y se pone al día sola al volver la conexión.

## Si algo falla

- El **aviso amarillo** de abajo a la izquierda dice qué pasa.
- `app.log` guarda los errores.
- `desinstalar.bat` cierra la app, quita el arranque automático, borra el permiso y restaura tu fondo.
- Ajustes (horas visibles, imagen de fondo, frecuencia...) en `config.json`; el [README](README.md#configuration) explica cada uno.

> No compartas `credentials.json` ni la carpeta `datos`: contienen tu acceso a Google.
