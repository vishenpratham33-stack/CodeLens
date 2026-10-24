// A very small service worker. It lets phones and tablets offer "Install app".
// It never stores anything: your files and searches always go to the server.
self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (event) { event.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", function () { /* pass everything through untouched */ });
