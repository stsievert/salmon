.. _frontendcustomization:

Frontend customization
======================

Custom HTML
-----------

As mentioned in the :class:`~salmon.triplets.manager.HTML`, it's possible to
include custom HTML in the query page by customizing the ``element_top``,
``element_middle``, ``element_bottom`` and ``element_standalone`` fields. You'll probably have to look
at `query_page.html`_ to see exactly the custom HTML elements are inserted.

.. _query_page.html: https://github.com/stsievert/salmon/blob/master/templates/query_page.html

For example, if you wanted to wanted to include a button with the showing "Skip
this question" and didn't want to set ``html.skip_button = true``, you could
follow this example:

.. code:: yaml

   html:
     # skip_button: true  # a much easier way to include the HTML code below!
     element_bottom: >
       <div class="d-flex align-items-end flex-column">
         <div id="skip-button" style="padding: 30px; padding-right: 60px;">
           <button type="button" class="btn btn-outline-secondary btn-sm" data-html="true"
                   onclick="getquery()" data-toggle="tooltip" data-placement="top"
               title="Skip questions only if you know <em>nothing</em> about the items shown."
           >Skip this question</button>
         </div>
       </div>

A much easier way to get this is to set ``html.skip_button = true`` in
``init.yml``.

CSS Styling
-----------

As mentioned in the :class:`~salmon.triplets.manager.HTML`, it's possible to
customize the CSS by including a CSS field in the YAML file. For example, let's
say you were asking about the similarity of different colors, and wanted the
background to be dark to provide better contrast. This YAML block in
``init.yml`` would implement that:

.. code:: yaml

   html:
     instructions: Which of the comparison colors is most similar to the target color?
     debrief: Thanks! Please enter this participant ID in the assignment. max_queries: 100  # about 2.94 minutes for 100 queries
     arrow_keys: True
     css: >
       body {
         background-color: #414141;
         color: #ddd;
       }
       .answer {
         background-color: #595959;
         border-color: #bbb;
       }
       .head {
         background-color: #505050;
         border-color: #000;
       }
       .debrief {
         color: #000;
       }
