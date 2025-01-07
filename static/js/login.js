document.querySelector(".sign-in-form").addEventListener("submit", function(event) {
    event.preventDefault(); // Prevent form from submitting

    // Get the input values
    const email = document.querySelector(".sign-in-form input[name='email']").value;
    const password = document.querySelector(".sign-in-form input[name='password']").value;

    // Create form data
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    // Send login request to the server
    fetch('/login', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Login successful!");
            window.location.href = "/home";
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("An error occurred. Please try again.");
    });
});
