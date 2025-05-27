#!/bin/bash

echo "Starting build process..."

# Create necessary directories if they don't exist
mkdir -p static
mkdir -p templates
mkdir -p uploads

echo "Created required directories"

# Ensure permissions are set correctly
chmod -R 755 static
chmod -R 755 templates
chmod -R 755 uploads

echo "Set directory permissions"

# Create static content directly in script
echo "/* Basic styles */" > static/homeStyle.css
echo "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');" >> static/homeStyle.css
echo "
:root {
    --bg-primary: #212529;
    --bg-secondary: #343a40;
    --bg-tertiary: #343a40;
    --text-primary: #dee2e6;
    --text-secondary: #adb5bd;
    --accent-color: #5d5cde;
    --border-color: #495057;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    width: 100%;
    height: 100%;
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    overflow-x: hidden;
}

a {
    text-decoration: none;
    color: inherit;
}

.container {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header and Navigation */
.site-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 50px;
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    background-color: var(--bg-primary);
    z-index: 100;
}

.logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.5rem;
    font-weight: 700;
}

.logo i {
    font-size: 1.8rem;
    color: var(--accent-color);
}

.main-nav {
    display: flex;
    align-items: center;
}

.nav-links {
    display: flex;
    list-style: none;
    gap: 30px;
}

.nav-links a {
    font-size: 1rem;
    font-weight: 500;
    color: var(--text-secondary);
    transition: all 0.3s ease;
    padding: 8px 12px;
    border-radius: 6px;
}

.nav-links a:hover, .nav-links a.active {
    color: var(--text-primary);
    background-color: var(--bg-secondary);
}

.primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background-color: var(--accent-color);
    color: white;
    padding: 12px 30px;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.primary-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(93, 92, 222, 0.2);
}
" >> static/homeStyle.css

echo "Created homeStyle.css"

echo "/* Basic styles */" > static/styles.css
echo "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');" >> static/styles.css
echo "
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --bg-primary: #212529;
    --bg-secondary: #343a40;
    --bg-tertiary: #343a40;
    --text-primary: #dee2e6;
    --text-secondary: #adb5bd;
    --accent-color: #5d5cde;
    --border-color: #495057;
    --sidebar-width: 280px;
}

html, body {
    width: 100%;
    height: 100%;
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
}

/* Layout */
.app-container {
    display: flex;
    height: 100vh;
    width: 100%;
}

/* Sidebar Styles */
.sidebar {
    width: var(--sidebar-width);
    height: 100vh;
    background-color: var(--bg-tertiary);
    border-right: 1px solid var(--border-color);
    position: fixed;
    left: 0;
    top: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding-bottom: 20px;
}

.sidebar-header {
    padding: 20px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    justify-content: space-between;
}

.sidebar-header h1 {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.file-limit-note {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
    font-style: italic;
}

.url-note {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
    font-style: italic;
}

.dark .file-limit-note,
.dark .url-note {
    color: var(--text-secondary);
}
" >> static/styles.css

echo "Created styles.css"

# List contents of static directory to verify
echo "Contents of static directory:"
ls -la static/

# Verify template files
if [ ! -f "templates/index.html" ] && [ -f "templates/Index.html" ]; then
  echo "Creating lowercase index.html from Index.html..."
  cp templates/Index.html templates/index.html
fi

# Create test file to verify static serving
echo "<html><body><h1>Static Test</h1></body></html>" > static/test.html

echo "Build script completed successfully!" 