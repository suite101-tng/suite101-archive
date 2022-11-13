define(['jquery'], function($) {
    'use strict';
    return {
       parallax: function(switchedOn) {
            var self = this;
            switchedOn = switchedOn || false;
            var $hero = this.$(".detailHero .heroImg")[0];

            var requestAnimationFrame = window.requestAnimationFrame || 
                                        window.mozRequestAnimationFrame || 
                                        window.webkitRequestAnimationFrame ||
                                        window.msRequestAnimationFrame;
             
            var transforms = ["transform", 
                              "msTransform", 
                              "webkitTransform", 
                              "mozTransform", 
                              "oTransform"];
                               
            var transformProperty = getSupportedPropertyName(transforms);    
            // var imageContainer = document.querySelector(".detailHero .heroImg");
            var imageContainer = $hero;       
            var scrolling = false;
            var mouseWheelActive = false;        
            var count = 0;
            var mouseDelta = 0;
      
            if(switchedOn) {
                self.parallaxOn = true;
                setup();      
            } else {
                self.parallaxOn = false;
                window.removeEventListener("scroll", setScrolling, false); 
                window.removeEventListener("mousewheel", mouseScroll, false);
                window.removeEventListener("DOMMouseScroll", mouseScroll, false);
                window.cancelAnimationFrame(requestAnimationFrame);
                return;
            }    

            function getSupportedPropertyName(properties) {
                for (var i = 0; i < properties.length; i++) {
                    if (typeof document.body.style[properties[i]] != "undefined") {
                        return properties[i];
                    }
                }
                return null;
            }
             
            function setup() {
                window.addEventListener("scroll", setScrolling, false); 
                window.addEventListener("mousewheel", mouseScroll, false);
                window.addEventListener("DOMMouseScroll", mouseScroll, false);
                animationLoop();
            }
             
            function mouseScroll(e) {
                mouseWheelActive = true;

                // if (e.preventDefault) {
                //     e.preventDefault();
                // }
                 
                if (e.wheelDelta) {
                    mouseDelta = e.wheelDelta / 120;
                } else if (e.detail) {
                    mouseDelta = -e.detail / 3;
                }
            }
             
            function setScrolling() {
                scrolling = true;
            }
             
            function getScrollPosition() {
                if (document.documentElement.scrollTop == 0) {
                    return document.body.scrollTop;
                } else {
                    return document.documentElement.scrollTop;
                }
            }
             
            function setTranslate3DTransform(element, yPosition) {
                var value = "translate3d(0px" + ", " + yPosition + "px" + ", 0)";
                element.style[transformProperty] = value;
            }
             
            function animationLoop() {
                if(!self.parallaxOn) {
                    window.cancelAnimationFrame(requestAnimationFrame);
                    return;
                }
                // adjust the image's position when scrolling
                if (scrolling) {
                    setTranslate3DTransform(imageContainer, 
                                            -1 * -getScrollPosition() / 3);
                    scrolling = false;
                }
                 
                // scroll up or down by 10 pixels when the mousewheel is used
                if (mouseWheelActive) {
                    window.scrollBy(0, -mouseDelta * 10);
                    count++;
                     
                    // stop the scrolling after a few moments
                    if (count > 20) {
                        count = 0;
                        mouseWheelActive = false;
                        mouseDelta = 0;
                    }
                }     
                requestAnimationFrame(animationLoop);
            }

        }

    }
})