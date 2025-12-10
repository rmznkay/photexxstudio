// Firebase configuration
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-analytics.js";
import { getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
import { getFirestore, collection, query, where, getDocs } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCGZUWaWFxmjfT6m_Tn4S_yk_tShOMGeX0",
  authDomain: "photexx-72.firebaseapp.com",
  projectId: "photexx-72",
  storageBucket: "photexx-72.firebasestorage.app",
  messagingSenderId: "652169477427",
  appId: "1:652169477427:web:091065d15745912a8cd246",
  measurementId: "G-203178FD5X"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const db = getFirestore(app);

// Login function - only allows users with firma field
async function loginUser(email, password) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    
    // Check if user has "firma" field in Firestore
    const usersRef = collection(db, "users");
    const q = query(usersRef, where("__name__", "==", user.uid));
    const querySnapshot = await getDocs(q);
    
    if (querySnapshot.empty) {
      await signOut(auth);
      throw new Error("Kullanıcı bulunamadı");
    }
    
    const userData = querySnapshot.docs[0].data();
    
    // Check if user has "firma" role or firma field
    if (!userData.firma && userData.role !== "firma") {
      await signOut(auth);
      throw new Error("Bu hesap firma yetkisine sahip değil");
    }
    
    return {
      success: true,
      user: user,
      userData: userData
    };
  } catch (error) {
    console.error("Login error:", error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Logout function
async function logoutUser() {
  try {
    await signOut(auth);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Auth state observer
function observeAuthState(callback) {
  return onAuthStateChanged(auth, callback);
}

export { auth, db, loginUser, logoutUser, observeAuthState };
