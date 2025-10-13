$(document).ready(function () {

    function handleJump() {

    }

    $(document).keydown(function (e) {
        let direction = null;
        console.log(e.which);

        switch (e.which) {
            case 32:
                handleJump();
                break;
            default: return;
        }

        if (direction) {
            e.preventDefault();
            sendSnakeDirection(direction);
        }

    });

})