//
// Inicio de sesión con Firebase Authentication
//

// Firebase SDKs
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
import {
  getAuth,
  signInWithPopup,
  GithubAuthProvider,
  GoogleAuthProvider,
  OAuthProvider,
} from "https://www.gstatic.com/firebasejs/12.6.0/firebase-auth.js";

// Definir los elementos del DOM
const loggedIn = document.getElementById("logged_in");
const loggedOut = document.getElementById("logged_out");
const usuarioNombre = document.getElementById("usuario_nombre");
const identityTokenFormContainer = document.getElementById("identity_token_form_container");
const identityTokenForm = document.getElementById("identity_token_form");
const signWithContainer = document.getElementById("sign_with_container")
const signWithGoogleButton = document.getElementById("sign_with_google");
const signWithMicrosoftButton = document.getElementById("sign_with_microsoft");
const signWithGitHubButton = document.getElementById("sign_with_gitHub");
const identityInput = document.getElementById("identidad");
const tokenInput = document.getElementById("token");
const errorContainer = document.getElementById("error_container");
const errorMessage = document.getElementById("error_message");

// Función para mostrar errores
function displayError(message, error = null) {
  if (errorContainer && errorMessage) {
    errorMessage.textContent = message;
    errorContainer.style.display = "block";
    // Auto-hide after 5 seconds
    setTimeout(() => {
      errorContainer.style.display = "none";
    }, 5000);
  }
  // Still log to console for debugging
  if (error) {
    console.error(message, error);
  }
}

// Función para ocultar errores
function hideError() {
  if (errorContainer) {
    errorContainer.style.display = "none";
  }
}

// Funcion para mostrar el mensaje de error según lo devuelto
function handleSignInError(error, provider, button) {
  // Re-enable and reset button
  button.textContent = `Ingresar con ${provider}`;
  button.disabled = false;
  let userMessage = `Error al iniciar sesión con ${provider}.`;
  const errorMessages = {
    'auth/popup-closed-by-user': 'La ventana de inicio de sesión fue cerrada.',
    'auth/popup-blocked': 'La ventana emergente fue bloqueada. Permite ventanas emergentes.',
    'auth/cancelled-popup-request': 'Solicitud de inicio de sesión cancelada.',
    'auth/network-request-failed': 'Error de red. Verifica tu conexión.',
    'auth/unauthorized-domain': 'Dominio no autorizado.',
    'auth/operation-not-allowed': `El inicio de sesión con ${provider} no está habilitado.`,
    'auth/account-exists-with-different-credential': 'Ya existe una cuenta con este correo.',
  };
  userMessage = errorMessages[error.code] || `Error: ${error.message}`;
  displayError(userMessage, error);
}

// Inicializar Firebase Authentication
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Función a ejecutar cuando se hace clic en el botón "Ingresar con Google"
function toogleSignWithGoogleButton() {
  if (!auth.currentUser) {
    hideError();
    // Abrir ventana emergente y cambiar el texto del botón a "Ingresar con Google"
    const googleProvider = new GoogleAuthProvider();
    googleProvider.addScope("https://www.googleapis.com/auth/userinfo.email");
    signInWithPopup(auth, googleProvider)
      .then((result) => {
        // Cambiar el texto del botón a "Cerrar cuenta de Google"
        signWithGoogleButton.textContent = "Cerrar cuenta de Google";
        signWithGoogleButton.disabled = false;
        // Deshabilitar y ocultar los otros botones
        signWithMicrosoftButton.disabled = true;
        signWithMicrosoftButton.style.display = "none";
        signWithGitHubButton.disabled = true;
        signWithGitHubButton.style.display = "none";
      })
      .catch((error) => {
        handleSignInError(error, "Google", signWithGoogleButton);
      });
  } else {
    // Cerrar sesión y cambiar el texto del botón a "Ingresar con Google"
    auth.signOut();
    identityTokenFormContainer.style.display = "none";
    signWithGoogleButton.textContent = "Ingresar con Google";
    signWithGoogleButton.disabled = false;
    // Mostrar todos los botones
    signWithGoogleButton.style.display = "block";
    signWithMicrosoftButton.style.display = "block";
    signWithGitHubButton.style.display = "block";
  }
}

// Función a ejecutar cuando se hace clic en el botón "Ingresar con Microsoft"
function toogleSignWithMicrosoftButton() {
  if (!auth.currentUser) {
    hideError();
    // Abrir ventana emergente y cambiar el texto del botón a "Ingresar con Microsoft"
    const microsoftProvider = new OAuthProvider("microsoft.com");
    microsoftProvider.addScope("User.Read");
    signInWithPopup(auth, microsoftProvider)
      .then((result) => {
        // Cambiar el texto del botón a "Cerrar cuenta de Microsoft"
        signWithMicrosoftButton.textContent = "Cerrar cuenta de Microsoft";
        signWithMicrosoftButton.disabled = false;
        // Deshabilitar y ocultar los otros botones
        signWithGoogleButton.disabled = true;
        signWithGoogleButton.style.display = "none";
        signWithGitHubButton.disabled = true;
        signWithGitHubButton.style.display = "none";
      })
      .catch((error) => {
        handleSignInError(error, "Microsoft", signWithMicrosoftButton);
      });
  } else {
    // Cerrar sesión y cambiar el texto del botón a "Ingresar con Microsoft"
    auth.signOut();
    identityTokenFormContainer.style.display = "none";
    signWithMicrosoftButton.textContent = "Ingresar con Microsoft";
    signWithMicrosoftButton.disabled = false;
    // Mostrar todos los botones
    signWithGoogleButton.style.display = "block";
    signWithMicrosoftButton.style.display = "block";
    signWithGitHubButton.style.display = "block";
  }
}

// Función a ejecutar cuando se hace clic en el botón "Ingresar con GitHub"
function toogleSignWithGitHubButton() {
  if (!auth.currentUser) {
    hideError();
    // Abrir ventana emergente y cambiar el texto del botón a "Ingresar con GitHub"
    const githubProvider = new GithubAuthProvider();
    githubProvider.addScope("read:user");
    signInWithPopup(auth, githubProvider)
      .then((result) => {
        // Cambiar el texto del botón a "Cerrar cuenta de GitHub"
        signWithGitHubButton.textContent = "Cerrar cuenta de GitHub";
        signWithGitHubButton.disabled = false;
        // Deshabilitar y ocultar los otros botones
        signWithGoogleButton.disabled = true;
        signWithGoogleButton.style.display = "none";
        signWithMicrosoftButton.disabled = true;
        signWithMicrosoftButton.style.display = "none";
      })
      .catch((error) => {
        handleSignInError(error, "GitHub", signWithGitHubButton);
      });
  } else {
    // Cerrar sesión y cambiar el texto del botón a "Ingresar con GitHub"
    auth.signOut();
    identityTokenFormContainer.style.display = "none";
    signWithGitHubButton.textContent = "Ingresar con GitHub";
    signWithGitHubButton.disabled = false;
    // Mostrar todos los botones
    signWithGoogleButton.style.display = "block";
    signWithMicrosoftButton.style.display = "block";
    signWithGitHubButton.style.display = "block";
  }
}

// Inicializar el proceso de inicio de sesión
function initLogin() {
  // Si firebaseConfig no está definido, deshabilitar los botones de inicio de sesión y salir
  if (typeof firebaseConfig === "undefined") {
    signWithGoogleButton.disabled = true;
    signWithGoogleButton.textContent = "Configuración no encontrada";
    signWithMicrosoftButton.disabled = true;
    signWithMicrosoftButton.textContent = "Configuración no encontrada";
    signWithGitHubButton.disabled = true;
    signWithGitHubButton.textContent = "Configuración no encontrada";
    return;
  }

  // Cuando cambia la autenticación
  auth.onAuthStateChanged((user) => {
    if (user) {
      // Usuario autenticado
      usuarioNombre.textContent = user.displayName ? user.displayName : "Usuario";
      loggedOut.style.display = "none";
      loggedIn.style.display = "block";
      // Llenar el formulario
      identityInput.value = user.email;
      user.getIdToken().then((token) => {
        tokenInput.value = token;
      });
      // Ocultar todos los botones
      signWithGoogleButton.style.display = "none";
      signWithMicrosoftButton.style.display = "none";
      signWithGitHubButton.style.display = "none";
      // Mostrar el boton para cerrar la cuenta usada
      user.providerData.forEach(data => {
        if (data["providerId"] === "google.com") {
          signWithGoogleButton.textContent = "Cerrar cuenta de Google";
          signWithGoogleButton.disabled = false;
          signWithGoogleButton.style.display = "block";
        }
        if (data["providerId"] === "microsoft.com") {
          signWithMicrosoftButton.textContent = "Cerrar cuenta de Microsoft";
          signWithMicrosoftButton.disabled = false;
          signWithMicrosoftButton.style.display = "block";
        }
        if (data["providerId"] === "github.com") {
          signWithGitHubButton.textContent = "Cerrar cuenta de GitHub";
          signWithGitHubButton.disabled = false;
          signWithGitHubButton.style.display = "block";
        }
      });
      // Mostrar el formulario para ingresar
      identityTokenFormContainer.style.display = "block";
    } else {
      // Usuario no autenticado
      console.log("Usuario NO autenticado");
      loggedOut.style.display = "block";
      loggedIn.style.display = "none";
      // Ocultar el formulario para ingresar
      identityTokenFormContainer.style.display = "none";
    }
  });

  // Habilitar el botón "Ingresar con Google"
  signWithGoogleButton.addEventListener("click", toogleSignWithGoogleButton);
  signWithGoogleButton.textContent = "Ingresar con Google";
  signWithGoogleButton.disabled = false;

  // Habilitar el botón "Ingresar con Microsoft"
  signWithMicrosoftButton.addEventListener("click", toogleSignWithMicrosoftButton);
  signWithMicrosoftButton.textContent = "Ingresar con Microsoft";
  signWithMicrosoftButton.disabled = false;

  // Habilitar el botón "Ingresar con GitHub"
  signWithGitHubButton.addEventListener("click", toogleSignWithGitHubButton);
  signWithGitHubButton.textContent = "Ingresar con GitHub";
  signWithGitHubButton.disabled = false;

  // Mostrar el contenedor con los botones
  signWithContainer.style.display = "block";

}

// Inicializar el inicio de sesión cuando termine la carga de la ventana
window.onload = initLogin;
