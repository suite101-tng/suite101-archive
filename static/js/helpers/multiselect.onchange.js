define(['jquery'], function($) {
    'use strict';
    var onchangeMethod = function($select) {
        var selectedOptions = $select.find('option:selected');
        var dropdown;
        if (selectedOptions.length >= 3) {
            // Disable all other checkboxes.
            var nonSelectedOptions = $select.find('option').filter(function() {
                return !$(this).is(':selected');
            });

            dropdown = $select.siblings('.multiselect-container');
            nonSelectedOptions.each(function() {
                var input = $('input[value="' + $(this).val() + '"]');
                input.prop('disabled', true);
                input.parent('li').addClass('disabled');
            });
        }
        else {
            // Enable all checkboxes.
            dropdown = $select.siblings('.multiselect-container');
            $select.find('option').each(function() {
                var input = $('input[value="' + $(this).val() + '"]');
                input.prop('disabled', false);
                input.parent('li').addClass('disabled');
            });
        }
    };
    return onchangeMethod;
});

