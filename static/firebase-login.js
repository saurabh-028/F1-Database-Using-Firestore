// Import Firebase authentication functions
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-auth.js";

// Your Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBpT-N-JFEeztcWFXsBIoE6ayy_bR4zL3k",
    authDomain: "f1-racing-c1506.firebaseapp.com",
    projectId: "f1-racing-c1506",
    storageBucket: "f1-racing-c1506.firebasestorage.app",
    messagingSenderId: "428068897753",
    appId: "1:428068897753:web:77c2ec2e83b2e870c94fc8"
  };

window.addEventListener("load", function () {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    
    // Get elements from the DOM
    const loginBox = document.getElementById("login-box");
    const errorMessage = document.getElementById("error-message");
    
    // Only proceed if we're on a page with login functionality
    if (loginBox) {
        updateUI(document.cookie);

        // Sign-up of a new user to Firebase
        document.getElementById("sign-up").addEventListener("click", function () {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            
            if (!email || !password) {
                showError("Please enter both email and password");
                return;
            }

            createUserWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    // User created successfully
                    const user = userCredential.user;
                    return user.getIdToken();
                })
                .then((token) => {
                    document.cookie = "token=" + token + "; path=/; SameSite=Strict";
                    window.location = "/";
                })
                .catch((error) => {
                    console.error("Signup Error:", error.code, error.message);
                    showError(error.message);
                });
        });

        // Login of a user to Firebase
        document.getElementById("login").addEventListener("click", function () {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            
            if (!email || !password) {
                showError("Please enter both email and password");
                return;
            }

            signInWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    // User signed in successfully
                    const user = userCredential.user;
                    return user.getIdToken();
                })
                .then((token) => {
                    document.cookie = "token=" + token + "; path=/; SameSite=Strict";
                    window.location = "/";
                })
                .catch((error) => {
                    console.error("Login Error:", error.code, error.message);
                    showError(error.message);
                });
        });
    }

    // Signout from Firebase (if sign-out button exists)
    const signOutBtn = document.getElementById("sign-out");
    if (signOutBtn) {
        signOutBtn.addEventListener("click", function () {
            signOut(auth)
                .then(() => {
                    document.cookie = "token=; path=/; SameSite=Strict";
                    window.location = "/";
                })
                .catch((error) => {
                    console.error("Logout Error:", error.message);
                });
        });
    }
});

// Function to show error messages
function showError(message) {
    const errorElement = document.getElementById("error-message");
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove("d-none");
        setTimeout(() => {
            errorElement.classList.add("d-none");
        }, 5000);
    }
}

// Function to update the UI depending on login state
function updateUI(cookie) {
    // This function is no longer needed in the new structure
    // since we handle UI changes via template rendering
    return;
}

// Function to extract the token from the cookie
function parseCookieToken(cookie) {
    if (!cookie) return "";
    var strings = cookie.split(";");
    for (let i = 0; i < strings.length; i++) {
        var temp = strings[i].trim().split("=");
        if (temp[0] === "token") return temp[1];
    }
    return "";
}