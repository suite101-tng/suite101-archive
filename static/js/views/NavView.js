define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'helpers/jquery.autoExpandTextarea',// noexports
    'lib/bindWithDelay', // noexports
],
function($,
    Backbone,
    _,
    suiteio
) {
    'use strict';
    var NavView = Backbone.View.extend({
        el: '[data-view-bind="NavView"]',

        events: function() {
            return _.extend({              
                // 'click .newStoryModal': 'newStoryModal'
            },
            _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            
            if(options) {
                if(options.el) {
                    this.setElement(options.el);
                }       
            }
        },    

        openDrawer: function() {
            console.log('openDrawer!');
            this.trigger('openDrawer');
        },

        closeDrawer: function() {
            this.trigger('closeDrawer');
        },

        toggleSearch: function(e) {
            suiteio.pageController.toggleSearch(e);
        },   
        
        loginModal: function() {
            suiteio.fireLoginModal();
        },

        // newStoryModal: function() {
        //     this.closeDrawer();
        //     this.trigger('fireNewStoryModal');
        // },

        destroy: function() {
            console.log('destroying navview');
        }
    });
    return NavView;
});