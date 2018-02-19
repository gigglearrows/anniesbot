function alias_changed(e) {
    var new_val = $(this).val().replace('!', '').replace(' ', '');
    $(this).val(new_val.toLowerCase());
    if (new_val.length == 0) {
        $('div.add-alias').addClass('disabled');
    } else {
        $('div.add-alias').removeClass('disabled');
    }
}

function get_aliases()
{
    var aliases = [];
    $('.form-horizontal div.field-alias div.aliases div').each(function(index, el) {
        aliases.push($(el).data('alias'));
    });

    return aliases;
}

function submit_form()
{
    $('form').form('validate form');
    if ($('form').form('is valid')) {
        $('form').form('submit');
    }
}

$(document).ready(function() {
    $('form').form({
        fields: {
            aliases: {
                identifier: 'aliases',
                rules: [
                {
                    type: 'empty',
                    prompt: 'You need at least one alias'
                }
                ]
            },
            level: {
                identifier: 'level',
                rules: [
                {
                    type: 'integer[1..2000]',
                    prompt: 'Please enter a valid command level (1-2000)'
                }]
            },
            cd: {
                identifier: 'cd',
                rules: [
                {
                    type: 'integer[0..999999]',
                    prompt: 'Please enter a valid cooldown'
                }]
            },
            usercd: {
                identifier: 'usercd',
                rules: [
                {
                    type: 'integer[0..999999]',
                    prompt: 'Please enter a valid user cooldown'
                }]
            },
            cost: {
                identifier: 'cost',
                rules: [
                {
                    type: 'integer[0..999999]',
                    prompt: 'Please enter a valid cost'
                }]
            },
            response: {
                identifier: 'response',
                rules: [
                {
                    type: 'empty',
                    prompt: 'The response cannot be empty'
                }
                ]
            },
        },
        keyboardShortcuts: false,
    });
    $('.btn.submit').click(function() {
        var input_el_length = $('input.alias').val().length;
        console.log(input_el_length);
        if (input_el_length > 0) {
            $('div.add-alias').api('query get request');
            var promise = $('div.add-alias').api('get request');
            if (promise !== false) {
                console.log(promise);
                promise.always(function() {
                    console.log('always');
                    submit_form();
                });
            } else {
                submit_form();
            }
        } else {
            submit_form();
        }
    });
    var $button = $('<div>', {'class': 'btn btn-success button-control add-alias disabled'}).html('<i class="fa fa-plus"></i> Add');
    $button.appendTo($('div.alias-button-bar'));
    $('input.alias').on('input', alias_changed);
    $('input.alias').on('change', alias_changed);
    $button.api({
        action: 'check_alias',
        method: 'post',
        beforeSend: function(settings) {
            var input_el = $(this).parent().parent().find('input.alias');
            $(this).parent().addClass('disabled');
            var alias = input_el.val();
            if (alias.length == 0) {
                return false;
            }

            var current_aliases = get_aliases();
            if (current_aliases.indexOf(alias) !== -1) {
                var el = $('.form-horizontal div.ui.message.warning');
                el.show();
                el.text('This alias is already in use.');
                setTimeout(function() {
                    el.hide();
                }, 2000);
                var input_el = $(this).parent().parent();
                input_el.removeClass('disabled');
                return false;
            }

            settings.data.alias = alias;
            return settings;
        },
        successTest: function(response) {
            return response.success || false;
        },
        onComplete: function() {
            var input_el = $(this).parent().parent();
            input_el.removeClass('disabled');
        },
        onSuccess: function(response, element, xhr) {
            var input_el = $(this).parent().parent().find('input.alias');

            var $div = $('<div>', {'class': 'label label-info'}).text(input_el.val() + ' ');
            $div.appendTo(input_el.parent().parent().find('div.aliases'));
            $div.data('alias', input_el.val());

            var $button = $('<a>', {'href': '#'}).html('<i class="fa fa-times color-red"></i>');
            $button.appendTo($div);
            $button.click(function() {
                $(this).parent().remove();
                $('input[name="aliases"]').val(get_aliases().join('|'))
            });

            input_el.val('');
            $('input[name="aliases"]').val(get_aliases().join('|'))
        },
        onFailure: function() {
            var el = $('.form-horizontal div.ui.message.warning');
            el.show();
            el.text('This alias is already in use.');
            setTimeout(function() {
                el.hide();
            }, 2000);
        }
    });

});
