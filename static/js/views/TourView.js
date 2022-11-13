//FlagView.js
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    suiteio
    ) {
    'use strict';
    var TourView = Backbone.View.extend({
        el: '[data-view-bind="TourView"]',
        events: function() {
            return _.extend({
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            this.tourModalPromise = suiteio.templateLoader.getTemplate('tour-modal');
            this.options = options || '';
            this.numCards = 7;
            this.cardIndex = 1;
        },

        changeCard: function() {
            var self = this;
            $('.navItem').removeClass('active');
            $('.tourCard').removeClass('active');
            $('[data-card="' + self.cardIndex + '"]').addClass('active');
        },

        loadTour: function() {
            var self = this;
            var i = 0;
            var numCards = self.numCards;
            var navItems = [];
                        
            while(++i <= numCards) {
                navItems.push(i);
            }
            console.log('navitems: ' + navItems);

            this.tourModalPromise.done(function(tmpl) {
                var $modal = $(tmpl({
                    navItems: navItems
                }));
                var $animDuration = 300;
                $modal.modal({expandIn: true, duration: $animDuration });

                $modal.on('keydown', function(e) {
                    var code = e.charCode || e.keyCode || e.which;
                    if(code === 39) { // right
                        e.preventDefault();
                        console.log('right');
                        if(self.cardIndex == self.numCards) {
                            self.cardIndex = 1;
                        } else {
                            self.cardIndex ++;
                        }
                        self.changeCard();
                    }
                    if(code === 37) { // left
                     console.log('left');
                        if(self.cardIndex == 1) {
                            self.cardIndex = self.numCards;
                        } else {
                            self.cardIndex --;
                        }
                        self.changeCard();
                    }
                });

                $modal.on('click', '.navItem', function(e) {
                    console.log('switching cards');
                    var $currentTarget = $(e.currentTarget);
                    self.cardIndex = $currentTarget.data('card');
                    self.changeCard();                   
                });

                // var interval = setInterval(function() {
                //     self.changeCard();
                // }, 5000); // change card every 5s
                                    
            });
        },

    });
    return TourView;
});