import ckan.plugins as p


@p.toolkit.auth_allow_anonymous_access
def archiver_resource_show(context, data_dict):
    # anyone
    return {'success': True}


@p.toolkit.auth_allow_anonymous_access
def archiver_dataset_show(context, data_dict):
    # anyone
    return {'success': True}


def archiver_package_show_or_initiate(context, data_dict):
    # Sysadmin only
    return {'success': False}


def archiver_resource_show_or_initiate(context, data_dict):
    # Sysadmin only
    return {'success': False}
