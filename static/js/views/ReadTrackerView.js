//ReadTrackerView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio'
],
function(
    $,
    Backbone,
    _,
    suiteio
) {
    'use strict';
    var ReadTrackerView = Backbone.View.extend({
        // el: 'body',

        initialize: function(options) {
            var self = this;
              var defaults = {
                    minHeight: 0,
                    elements: [],
                    percentage: true,
                    userTiming: true,
                    pixelDepth: true,
                    nonInteraction: true
                  };

            var $window = $(window);
            
            if(options.el) {
                this.setElement(options.el); //this view assumes el to be the .pageContainer
            }
            this.viewing = options.viewing;
            this.inf = options.rtInf;
            this.rto = this.inf.rto;
            this.dist = this.inf.dist || 1;

            this.sendTrackEvent('pvs');
            this.trigger('sendStoryView');
            this.startTime = +new Date;
            this.progress = 0;

            this.rtoReached = false;
            this.tpReached = false;
            this.readSent = false;

            var storyHeight = this.$('article').height(),
                winHeight = window.innerHeight ? window.innerHeight : $window.height();
            this.scrollHeight = storyHeight - winHeight;
            this.headerHeight = this.$('header').height();

            if((storyHeight - this.headerHeight) > (winHeight)) {
                this.rollinEnabled = true;
            } else {
                this.rollinEnabled = false;
            }
            
            if(this.scrollHeight && this.scrollHeight > 0) {
                this.targetPos = this.dist*100;
            } else { 
                this.targetPos = 0;
                this.gcCheckAtInterval();
            }

            this.dotPos = this.$('.dotMarker:visible').position();
            var stickHeight = 64 + 1;

            // Check Gateway Conditions on scroll
            $window.scroll(function () {        
                var scrollTop = $window.scrollTop() 
                var progress = scrollTop/self.scrollHeight * 100;
                var dotDistance = scrollTop + winHeight - self.dotPos.top - stickHeight;
                if(self.rollinEnabled) {
                    // self.stickUnstickActions(dotDistance);
                } 

                if(!self.readSent && self.gcMet(progress)){
                    self.sendTrackEvent('reads');
                    self.readSent = true; // switch it off
                } 
            });
        },

        stickUnstickActions: function(distance) {
            var self = this;
            if(distance>=0) {
                self.$('.storyRollin').get(0).classList.remove('stick');             
            } else {
                self.$('.storyRollin').get(0).classList.add('stick');             
            }
        },

        gcCheckAtInterval: function() {
            var self = this;
            var delay = 3000;
            var wait = setTimeout(function() { 
                if(!self.readSent && self.gcMet(self.progress)){
                    self.sendTrackEvent('reads');
                    self.readSent = true; // switch it off
                } else {
                    self.gcCheckAtInterval();
                }
            }, delay);
        },

        gcMet: function(progress) {
            var timer = +new Date - this.startTime;
            if(progress >= this.targetPos && timer >= this.rto) {
                this.gcMet = true;
                return true;
            } else { 
                return false; 
            }
        },

        sendTrackEvent: function(eventType) {
            var eventData = {
                "event": eventType,
                "story": this.inf.storyId,
                "user": this.inf.authorId,
                "chi": this.inf.chi,
                "royal": this.inf.royal,
                "viewing": this.viewing,
            };
            suiteio.eventRouter(eventData);
        },

        destroy: function() {
            $(window).unbind('scroll');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return ReadTrackerView;
});