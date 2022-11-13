//PaymentListView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'helpers/Lazyloader'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Lazyloader
) {
    'use strict';
    var PaymentListView = Backbone.View.extend({
        el: '[data-view-bind="PaymentListView"]',
        events: function() {
            return _.extend({
                'click .completePayment': 'completePayment'
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            console.log('hello and welcome');
                        this.lazyloader = new Lazyloader({
                delay: 200,
                url: window.location,
                data: {},
                dataType: 'text',
                threshold: 200,
                id: 'moderatepaymentsview', //to identify and namespace events
                contentContainer: this.$el,
                renderContext: this,
                render: this.appendNextPage,
                semiautomatic: false,
                success: function() {
                    // self.appendLoadMoreBtn();
                },
                error: function() {
                    // self.$('.loadMoreBtn').remove();
                }
            });
            this.lazyloader.getNextPage();
        },
        appendNextPage: function(objects) {
            this.$('.userList').append(objects);
            this.$('.popoverLink').popover({});
        },

        completePayment: function(e) {
            var $target = $(e.currentTarget),
                url = $target.attr('href');
                console.log(url);
                console.log('asfd asf safd ads f');
            $.ajax({
                url: url,
                type: 'POST',
                data: {},
                success: function() {
                    $('.completePayment').addClass('faded green'); 
                }
            });
        },



    });
    return PaymentListView;
});