.. _upload:

Documents Uploading
===================

All of the document uploading API endpoints follow the same set of rules.

Upload document with registration
---------------------------------

#. :ref:`Register document upload in document service <documentservice:register-document-upload>`.

#. Add document in API:

    .. http:example:: ../belowthreshold/http/tutorial/upload-tender-notice.http
        :code:

#. :ref:`Upload document in document service <documentservice:upload-document>`.

Upload document w/o registration
--------------------------------

#. :ref:`Register document upload in document service <documentservice:upload-document-w-o-registration>`.

#. Add document in API:

    .. http:example:: ../belowthreshold/http/tutorial/upload-tender-notice.http
        :code:


:ref:`Follow the link to see more document request examples <bt-documents-tutorial>`.
