document.addEventListener('DOMContentLoaded', function () {
    var hidSocket = io.connect('http://' + document.domain + ':' + location.port);
    var isFullscreen = false
    var activeModifiers = []
    var locked = false
    var noKeyWithMods = false
    
    var mouseScaling = 1.75
    
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    var cfg = undefined
    var xhr = new XMLHttpRequest()
    xhr.onload = function() {
        cfg = JSON.parse(xhr.responseText)
    }
    xhr.open("GET", "/api/dump_settings")
    xhr.send()
    
    // mouse handling
    async function handleMouseMove(event) {
        var movementX = event.movementX || event.mozMovementX || event.webkitMovementX || 0;
        var movementY = event.movementY || event.mozMovementY || event.webkitMovementY || 0;

        hidSocket.emit('mouse', `${Math.floor(movementX * mouseScaling)}|${Math.floor(movementY * mouseScaling)}`)
        await sleep(cfg["mouse"]["samplingRate"])
    }

    document.getElementById("stream").addEventListener('mouseover', function() {
        if (!locked) {
            document.getElementById("stream").requestPointerLock();
            locked = true
        } else {
            locked = false
        }
    })

    // click handling

    document.getElementById("stream").addEventListener("dblclick", function() {
        document.getElementById('stream').requestFullscreen();
    })
    
    document.getElementById("stream").addEventListener('mousedown', function(e) {
        clickAnyway = true
        if (!locked) { // lock if not locked
            document.getElementById("stream").requestPointerLock();
            locked = true
            return // return cause it'll click at a random point if we let it click
        }

        if (e.which === 1 || e.button === 0)
        {
            if (isFullscreen || clickAnyway) {
                hidSocket.emit("click", "left")
            } else {
                document.getElementById('stream').requestFullscreen();
            }
        }
    
        if (e.which === 2 || e.button === 1)
        {
            console.log('"Middle" at ' + e.clientX + 'x' + e.clientY);
            if (isFullscreen || clickAnyway) {
                hidSocket.emit("click", "middle")
            } else {
                document.getElementById('stream').requestFullscreen();
            }
        }
    
        if (e.which === 3 || e.button === 2)
        {
            console.log('"Right" at ' + e.clientX + 'x' + e.clientY);

            if (isFullscreen || clickAnyway) {
                hidSocket.emit("click", "right")
            } else {
                document.getElementById('stream').requestFullscreen();
            }

        }
    
        if (e.which === 4 || e.button === 3)
        {
            console.log('"Back" at ' + e.clientX + 'x' + e.clientY);
        }
    
        if (e.which === 5 || e.button === 4)
        {
            console.log('"Forward" at ' + e.clientX + 'x' + e.clientY);
        }
    })



    // scroll handling
    function handleWheel(event) {
        // Access scroll information from the event
        var delta = Math.floor(((event.deltaY || event.detail || event.wheelDelta)*-1) / 18);
        
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

                noKeyWithMods = true
                console.log("enabled nokeywmods")
                
                hidSocket.emit('modifiers', activeModifiers.join(','))
                try {
                    document.getElementById('mods').innerHTML = activeModifiers.join(', ')
                } catch {
                    console.log("failed to find a 'mods' element")
                }

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
                    console.log(cfg["keyboard"]["pasteSleep"]["value"])
                    await sleep(parseInt(cfg["keyboard"]["pasteSleep"]["value"]))
                }

                hidSocket.emit('modifiers', activeModifiers.join(','))

                return
            }
        } else { // if it's an actual key
            if (noKeyWithMods) {
                noKeyWithMods = false;
                console.log("disabled nokeywmods")

            }
        }

        console.log(e.key.toString())
        hidSocket.emit('keystroke', e.key.toString())
    });

    document.addEventListener('keyup', function(e) {
        e.preventDefault();
        e = e || window.event;

        if (['Meta', 'Control', 'Alt', 'Shift'].includes(e.key.toString())) {
            if (noKeyWithMods) {
                hidSocket.emit('keystroke', e.key.toString())
                noKeyWithMods = false
                console.log("disabled nokeywmods due to keyup")
            }

            activeModifiers.pop(e.key.toString())

            try {
                document.getElementById('mods').innerHTML = activeModifiers.join(', ')
            } catch {
                console.log("failed to find a 'mods' element")
            }

            hidSocket.emit('modifiers', activeModifiers.join(','))

            console.log(activeModifiers)

        }
    })

    // aux keys handling (counts as keybord i GUESS)
    function genTopRow() {
        function generateButton(buttonHTML, keyVal) {
            var key = document.createElement('button')

            key.innerHTML = buttonHTML
            key.addEventListener('click', function() {
                hidSocket.emit('keystroke', keyVal)
                console.log("keypress")
            })

            document.getElementById('toprow').appendChild(key)
        }

        generateButton(`Esc`, 'Escape')
        for (var f=1; f<13; f++) {
            generateButton(`F${f}`, `F${f}`)
        }
        generateButton(`Del`, 'Delete')
        generateButton(`Ins`, 'Insert')
        generateButton(`Home`, 'Home')
        generateButton(`PgUp`, 'PgUp')
        generateButton(`PgDn`, 'PgDown')
        generateButton(`End`, 'End')
        generateButton(`PrtScn`, 'PrtScn')
        generateButton(`SLock`, 'ScrollLock')
        generateButton(`Pause`, 'Pause')
    }



    
    // fullscreen handling
    document.addEventListener('pointerlockchange', function () {
        if (document.pointerLockElement === document.getElementById('stream')) {
            // Cursor is locked, add event listener for movement
            document.addEventListener('wheel', handleWheel)
        } else {
            // Cursor is unlocked, remove event listener for movement
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
    
    genTopRow()
    document.getElementById('stream').addEventListener('mousemove', handleMouseMove);
});