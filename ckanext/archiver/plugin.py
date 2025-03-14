import json
import logging

from ckan import model
from ckan import plugins as p

from ckanext.archiver.interfaces import IPipe
from ckanext.archiver.logic import action, auth
from ckanext.archiver import helpers
from ckanext.archiver import lib
from ckanext.archiver.model import Archival, aggregate_archivals_for_a_dataset
from ckanext.archiver import cli
from ckan.lib.plugins import DefaultTranslation

log = logging.getLogger(__name__)


class ArchiverPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm, DefaultTranslation):
    """
    Registers to be notified whenever CKAN resources are created or their URLs
    change, and will create a new ckanext.archiver celery task to archive the
    resource.
    """
    p.implements(p.ITranslation, inherit=True)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IClick)


    # IDomainObjectModification

    def notify(self, entity, operation=None):
        print("Archiver123", entity, operation)
        if not isinstance(entity, model.Package):
            return

        log.debug('Notified of package event: %s %s', entity.name, operation)

        run_archiver = \
            self._is_it_sufficient_change_to_run_archiver(entity, operation)
        if not run_archiver:
            print("Archiver_1")
            return

        log.debug('Creating archiver task: %s', entity.name)

        print("Archiver_2")
        lib.create_archiver_package_task(entity, 'QA')


    def _is_it_sufficient_change_to_run_archiver(self, package, operation):
        ''' Returns True if in this revision any of these happened:
        * it is a new dataset
        * dataset licence changed (affects qa)
        * there are resources that have been added or deleted
        * resources have changed their URL or format (affects qa)
        '''
        if operation == 'new':
            log.debug('New package - will archive')
            # even if it has no resources, QA needs to show 0 stars against it
            return True
        elif operation == 'deleted':
            log.debug('Deleted package - won\'t archive')
            return False
        # therefore operation=changed
        else:
            return True


    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')


    # IActions

    def get_actions(self):
        return {
            'archiver_resource_show': action.archiver_resource_show,
            'archiver_dataset_show': action.archiver_dataset_show,
            'archiver_package_show_or_initiate': action.archiver_package_show_or_initiate,
            'archiver_resource_show_or_initiate': action.archiver_resource_show_or_initiate,
            }


    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'archiver_resource_show': auth.archiver_resource_show,
            'archiver_dataset_show': auth.archiver_dataset_show,
            'archiver_package_show_or_initiate': auth.archiver_package_show_or_initiate,
            'archiver_resource_show_or_initiate': auth.archiver_resource_show_or_initiate,
            }


    # ITemplateHelpers

    def get_helpers(self):
        return dict((name, function) for name, function
                    in list(helpers.__dict__.items())
                    if callable(function) and name[0] != '_')


    # IPackageController

    def _add_to_pkg_dict(self, pkg_dict):
        archivals = Archival.get_for_package(pkg_dict['id'])
        if not archivals:
            return

        # dataset
        dataset_archival = aggregate_archivals_for_a_dataset(archivals)
        pkg_dict['archiver'] = dataset_archival

        # resources
        archivals_by_res_id = dict((a.resource_id, a) for a in archivals)
        for res in pkg_dict['resources']:
            archival = archivals_by_res_id.get(res['id'])
            if archival:
                archival_dict = archival.as_dict()
                del archival_dict['id']
                del archival_dict['package_id']
                del archival_dict['resource_id']
                res['archiver'] = archival_dict


    def before_dataset_view(self, pkg_dict):
        self._add_to_pkg_dict(pkg_dict)
        return pkg_dict

    
    def after_dataset_show(self, context, pkg_dict):
        # Insert the archival info into the package_dict so that it is
        # available on the API.
        # When you edit the dataset, these values will not show in the form,
        # it they will be saved in the resources (not the dataset). I can't see
        # and easy way to stop this, but I think it is harmless. It will get
        # overwritten here when output again.
        self._add_to_pkg_dict(pkg_dict)


    def before_dataset_index(self, pkg_dict):
        '''
        remove `archiver` from index
        '''
        pkg_dict.pop('archiver', None)
        for key, value in pkg_dict.items():
            if isinstance(value, dict):
                pkg_dict[key] = json.dumps(value)
        return pkg_dict


    # IClick

    def get_commands(self):
        return cli.get_commands()



class TestIPipePlugin(p.SingletonPlugin):
    """
    """
    p.implements(IPipe, inherit=True)

    def __init__(self, *args, **kwargs):
        self.calls = []

    def reset(self):
        self.calls = []

    def receive_data(self, operation, queue, **params):
        self.calls.append([operation, queue, params])
