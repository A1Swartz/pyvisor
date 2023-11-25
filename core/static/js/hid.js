document.addEventListener('DOMContentLoaded', function () {
    var hidSocket = io.connect('http://' + document.domain + ':' + location.port);
    var oldMouseX = 0
    var oldMouseY = 0
    var isFullscreen = false
    var activeModifiers = []
    var config = undefined

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    var xhr = new XMLHttpRequest()
    xhr.onload = function() {
        config = JSON.parse(xhr.responseText)
    }
    xhr.open("GET", "/api/dump_settings")
    xhr.send()
    
    // mouse handling
    document.getElementById("video_frame").addEventListener('mousemove', async function a(evt) {
        const mPos = getMousePos(evt);
        var x = Math.round(mPos.x - oldMouseX)
        var y = Math.round(mPos.y - oldMouseY)
        
        //console.log(`Mouse position x:${x}  y:${x}`)
        hidSocket.emit('mouse', `${x}|${y}`)
        
        oldMouseX = mPos.x
        oldMouseY = mPos.y
    });

    const getMousePos = (evt) => {
        const pos = evt.currentTarget.getBoundingClientRect();
        return {
            x: Math.round(evt.clientX - pos.left),
            y: Math.round(evt.clientY - pos.top)
        };
    };

    function handleMouseMove(event) {
        // Use movementX and movementY to get cursor movement
        var movementX = event.movementX || event.mozMovementX || event.webkitMovementX || 0;
        var movementY = event.movementY || event.mozMovementY || event.webkitMovementY || 0;

        if (isFullscreen) {
            // Do something with the movement information
            hidSocket.emit('mouse', `${movementX}|${movementY}`)
        }
    }

    // click handling
    document.getElementById("stream").addEventListener('click', function a() {
        if (isFullscreen) {
            hidSocket.emit("click", "left")
        } else {
            document.getElementById('stream').requestFullscreen();
        }
    });

    document.getElementById("stream").addEventListener('contextmenu', function a() {
        if (isFullscreen) {
            hidSocket.emit("click", "right")
        } else {
            document.getElementById('stream').requestFullscreen();
        }
    });

    document.getElementById("stream").addEventListener('onauxclick', function a() {
        if (isFullscreen) {
            hidSocket.emit("click", "middle")
        } else {
            document.getElementById('stream').requestFullscreen();
        }
    });




    // scroll handling
    function handleWheel(event) {
        // Access scroll information from the event
        var delta = (event.deltaY || event.detail || event.wheelDelta)*-1;
        
        // Do something with the scroll information
        console.log("Scroll delta:", delta);
        hidSocket.emit('scroll', `S:${delta}`)
    }
    


    // keyboard handling
    document.addEventListener("keydown", async function(e) {
        e.preventDefault();
        e = e || window.event;
        // Add scripts here

        if (e.key.toString() == " ") {
            hidSocket.emit('keystroke', "space")
            return
        }
        else if (['Meta', 'Control', 'Alt', 'Shift'].includes(e.key.toString())) { // check if its a modifier key
            if (!activeModifiers.includes(e.key.toString())) { // if its not already pressed
                activeModifiers.push(e.key.toString()) // append it to active modifiers
                
                hidSocket.emit('modifiers', activeModifiers.join(','))
            }
            return
        } else if (activeModifiers.includes("Control") || activeModifiers.includes("Alt")) {
            if (e.key.toString() == "v") {
                activeModifiersBefore = activeModifiers

                hidSocket.emit('modifiers', ",")

                navigator.permissions.query({ name: "clipboard-read" });
                var clipboardText = await navigator.clipboard.readText();
                var clipArray = clipboardText.split('')

                console.log(clipArray)
                console.log(`clipboard data: ${clipboardText}`)

                for (var i=0; i<clipArray.length; i++) {
                    console.log(clipArray[i])
                    hidSocket.emit('keystroke', clipArray[i])
                    console.log(config["keyboard"]["pasteSleep"]["value"])
                    await sleep(parseInt(config["keyboard"]["pasteSleep"]["value"]))
                }

                hidSocket.emit('modifiers', activeModifiers.join(','))

                return
            }
        }

        hidSocket.emit('keystroke', e.key.toString())
    });

    document.addEventListener('keyup', function(e) {
        e.preventDefault();
        e = e || window.event;

        if (['Meta', 'Control', 'Alt', 'Shift'].includes(e.key.toString())) {
            activeModifiers.pop(e.key.toString())

            hidSocket.emit('modifiers', activeModifiers.join(','))

            console.log(activeModifiers)

        }
    })



    
    // fullscreen handling
    document.addEventListener('pointerlockchange', function () {
        if (document.pointerLockElement === document.getElementById('stream')) {
            // Cursor is locked, add event listener for movement
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('wheel', handleWheel)
        } else {
            // Cursor is unlocked, remove event listener for movement
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('wheel', handleWheel);
        }
    });

    document.addEventListener("fullscreenchange", function() {
        if (document.fullscreenElement) {
            console.log(
            `Element: ${document.fullscreenElement.id} entered fullscreen mode.`,
            );
            document.getElementById("stream").requestPointerLock();
            isFullscreen = true
        } else {
            console.log("Leaving fullscreen mode.");
            isFullscreen = false
        }
    });
});