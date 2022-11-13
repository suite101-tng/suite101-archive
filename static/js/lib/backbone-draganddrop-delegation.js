(function ($) {
    var event,
        getEvent = function () {
            return event || window.event;
        },
        setEvent = function (ev) {
            event = ev;
        };

    // FireFox does not have a global event object.
    // By capturing the mousedown event on the window
    // we create our own event object
    // TODO: Check if window.event exists or not
    if (navigator.userAgent.toLowerCase().indexOf('firefox') >= 0) {
        window.addEventListener('mousedown', setEvent, true);
    }
    $.fn.extend({
        detectDrag: function () {
            var isDragging = false,
                dragStart = null,
                $clone = null,
                $el = null,
                data = {
                    set: function (value) {
                        data = value;
                    }
                },
                $dragoverElement = null,
                preventSelection = function (event) {
                    event.preventDefault();
                    return false;
                },
                dragDetected = function (event) {
                    return (Math.abs(dragStart.x - event.clientX) > 5 || Math.abs(dragStart.y - event.clientY) > 5)
                },
                startDrag = function (event) {
                    isDragging = true;
                    $clone = $el.clone().css({
                        position: 'absolute',
                        translateX: event.clientX + 5,
                        translateY: event.clientY + 5
                    }).appendTo('body');
                    // Make sure nothing can be input while dragging, causing drag stop
                    $('input, textarea').blur();
                    // Will get the returned value of any dragstart
                    // triggered event and set it as data
                    $el.trigger('dragstart', [data, $clone, $el]);
                },
                drag = function (event) {
                    var $target = $(event.target),
                        isNewTarget = $target[0] !== ($dragoverElement ? $dragoverElement[0] : null);
                    if ($target.attr('dropable') && isNewTarget) {
                        $dragoverElement = $target;
                        $target.trigger('dragenter', [$clone, $el]);
                    } else if ($dragoverElement && isNewTarget) {
                        $dragoverElement.trigger('dragleave', [$clone, $el]);
                        $dragoverElement = null;
                    }
                    $clone.css({
                        left: event.clientX + 5,
                        top: event.clientY + 5
                    });
                },
                handleDrag = function (event) {
                    if (isDragging) {
                        drag(event);
                    } else if (dragDetected(event)) {
                        startDrag(event);
                    }
                },
                stopDrag = function (event) {
                    var $target = $(event.target),
                        $window = $(window);
                    if (isDragging) {
                        $clone.remove();
                        if ($target.attr('dropable')) {
                            $target.trigger('drop', [data, $clone, $el]);
                        } else {
                            $el.trigger('dragend', [$clone, $el]);
                        }
                    }
                    isDragging = false;
                    $el.off('selectstart', preventSelection);
                    $('body').css('user-select', 'auto');
                    $window.off('mousemove', handleDrag).off('mouseup', stopDrag);
                };
            dragStart = {
                x: getEvent().clientX,
                y: getEvent().clientY
            };
            $el = $(this);
            $el.on('selectstart', preventSelection);
            $('body').css('user-select', 'none');
            $(window).on('mousemove', handleDrag).on('mouseup', stopDrag);
        }
    });
}(jQuery));