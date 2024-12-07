document.getElementById("registerButton").addEventListener("click", function(event) {
    event.preventDefault(); 

    // Get the input values
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    // Check if the username and password are filled
    if (username && password) {
      if (password.length < 8) {
        alert("Password must be at least 8 characters long.");
      } else {
        alert("Registration successful!");
      }
    } else {
      alert("Please fill in all the fields.");
    }
  });