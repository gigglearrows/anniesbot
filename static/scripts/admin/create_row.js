function enable_edit_row(base)
{
    $('.btn.edit-row').click(function() {
        var id = $(this).parent().parent().data('id');
        document.location.href = '/admin/' + base + '/edit/' + id;
    });
}

function enable_remove_row(modal_class, action)
{
	var id_remove = 0;
    $('.btn.remove-row').click(function() {
        id_remove = $(this).parent().parent().data('id');
        $('.modal.' + modal_class).modal('show');
    });
    $('.btn.' + modal_class + '-modal').api({
        action: action,
		successTest: function(response) {
            return response.success || false;
        },
		beforeSend: function(settings) {
			settings.urlData.id = id_remove;
			return settings;
		},
        
        onSuccess: function(response, element) {
            $('tr[data-id="' + id_remove + '"]').remove();
        },
        onFailure: function(response, element) {
            console.error('something went wrong');
        },

    });
}

function enable_toggle_row(action)
{
    $('.btn.toggle-row').api({
        action: action,
        method: 'post',
        successTest: function(response) {
            return response.success || false;
        },
        beforeSend: function(settings) {
            var state = $(this).parent().parent().data('enabled');
            console.log(state);
            settings.urlData.id = $(this).parent().parent().data('id');
            if (state == '1') {
                settings.data.new_state = 0;
            } else {
                settings.data.new_state = 1;
            }
            return settings;
        },
        onSuccess: function(response, element) {
            $(this).parent().parent().data('enabled', response.new_state);
            if (response.new_state == 1) {
                $(element).find('.text').text(' Disable');
                $(element).find('.fa').removeClass('color-green').addClass('color-red');
            } else {
                $(element).find('.text').text(' Enable');
                $(element).find('.fa').removeClass('color-red').addClass('color-green');
            }
        },
    });
}
