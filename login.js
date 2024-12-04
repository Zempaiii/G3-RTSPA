document.querySelector(".sign-in-form").addEventListener("submit", function(event) {
    event.preventDefault(); // Prevent form from submitting

    // Get the input values
    const username = document.querySelector(".sign-in-form input[type='text']").value;
    const password = document.querySelector(".sign-in-form input[type='password']").value;

    // Example credentials (for testing lang toh)
    const users = [
        { username: "user1", password: "password123" },
        { username: "user2", password: "password456" }
    ];

    // Checking if the username exists
    const user = users.find(user => user.username === username);

    // If user exists, check password
    if (user && user.password === password) {
        alert("Login successful!");
        // Redirect na dapat sa main/homepage
        window.location.href = ".html"; 
    } else if (user) {
        alert("Incorrect password.");
    } else {
        alert("Username does not exist.");
    }
});
