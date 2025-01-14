document.getElementById("registerButton").addEventListener("click", function(event) {
    event.preventDefault(); 

    // Get the input values
    const username = document.getElementById("username")?.value;
    const password = document.getElementById("password")?.value;
    const email = document.getElementById("email")?.value;
    const confirm = document.getElementById("confirm")?.value;

    const formData = new FormData();
    formData.append('em', email);
    formData.append('pw', password);
    formData.append('un', username);
    formData.append('cf', confirm);

    // Check if the username and password are filled
    if (username && password && email && confirm) {
        if (password.length < 8) {
            alert("Password must be at least 8 characters long.");
            return;
        }
        if (email !== confirm) {
            alert("Emails do not match.");
            return;
        }

        // Send the data to the server using POST method
        fetch('/register', {
          method: 'POST',
          body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Registration successful! Redirecting to verification page.");
                window.location.href = "/verify";
            } else {
                alert("Registration failed: " + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("An error occurred during registration. error: " + error);
        });
    } else {
        alert("Please fill in all the fields.");
    }
});