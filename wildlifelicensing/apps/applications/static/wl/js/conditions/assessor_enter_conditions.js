define([
  "jQuery",
  "lodash",
  "js/entry/application_preview",
  "select2",
], function ($, _, applicationPreview) {
  var $conditionsTableBody = $("#conditionsBody"),
    $conditionsEmptyRow = $("#conditionsEmptyRow"),
    $createCustomConditionModal = $("#createCustomConditionModal");

  function initApplicationDetailsPopover(application, formStructure) {
    var $contentContainer = $("<div>"),
      $viewApplicationDetails = $("#viewApplicationDetails");

    applicationPreview.layoutPreviewItems(
      $contentContainer,
      formStructure,
      application.data
    );

    require(["bootstrap"], function (bootstrap) {
      new bootstrap.Popover($viewApplicationDetails[0], {
        container: "body",
        content: $contentContainer,
        html: true,
      });
    });
  }

  function initAssignee(assessment, csrfToken, assessorsList, userID) {
    var $assignee = $("#assignee");

    assessorsList = assessorsList.map(function(o) {
      return { id: String(o.id), text: o.text };
    });

    $assignee.select2({
      theme: "bootstrap-5",
      data: assessorsList,
    });

    function forceUpdateSelect2(id) {
      if (id === undefined || id === null) return;
      
      var targetId = String(id);
      
      $assignee.val(targetId).trigger("change", { triggeredBy: "assignToMe" });
      
      $assignee.trigger("change.select2");
    }

    if (assessment.assigned_assessor) {
      forceUpdateSelect2(assessment.assigned_assessor.id);
    } else {
      forceUpdateSelect2(0);
    }

    $assignee.on("change", function (e, params) {
      // If the change was triggered programmatically by 'assignToMe', skip the AJAX call
      // because the data has already been saved to the server.
      if (params && params.triggeredBy === "assignToMe") {
        return;
      }

      var selectedUserId = $(this).val();

      if (!selectedUserId) return;

      $.post(
        "/applications/assign-assessor/",
        {
          assessmentID: assessment.id,
          csrfmiddlewaretoken: csrfToken,
          userID: selectedUserId,
        },
        function (data) {
          // Update processing status or other UI elements if needed
        }
      );
    });

    $("#assignToMe").off("click").on("click", function (e) {
      e.preventDefault();
      $.post(
        "/applications/assign-assessor/",
        {
          assessmentID: assessment.id,
          csrfmiddlewaretoken: csrfToken,
          userID: userID,
        },
        function (data) {
          if (data && data.assigned_assessor) {
            forceUpdateSelect2(data.assigned_assessor.id);
          }
        }
      );
    });
  }

  function initOtherAssessorsCommentsPopover(assessments) {
    var $contentContainer = $("<div>"),
      $viewOtherAssessorsComments = $("#viewOtherAssessorsComments");

    if (assessments.length) {
      $.each(assessments, function (index, assessment) {
        if (assessment.status === "Assessed") {
          var assessorGroupName =
            "<strong>" + assessment.assessor_group.name + ": </strong>";
          $contentContainer.append(
            $("<p>").html(assessorGroupName + assessment.comment)
          );
        }
      });
    }

    if ($contentContainer.children().length) {
      $contentContainer.find(":last-child").addClass("no-margin");
    } else {
      $contentContainer.append(
        $("<p>")
          .addClass("no-margin")
          .text("No other assessors' comments available")
      );
    }

    require(["bootstrap"], function (bootstrap) {
      new bootstrap.Popover($viewOtherAssessorsComments[0], {
        container: "body",
        content: $contentContainer,
        html: true,
      });
    });
  }

  function createConditionTableRow(condition, rowClass, readonly) {
    var $row = $("<tr>").addClass(rowClass);

    $row.append($("<td>").html(condition.code));
    $row.append($("<td>").html(condition.text));

    var $remove = $("<a>Remove</a>").attr("href", "#").attr("role", "button");
    $remove.click(function (e) {
      e.preventDefault(); // Prevent default action for the link
      $row.remove();

      if ($conditionsTableBody.find("tr").length == 1) {
        $conditionsEmptyRow.removeClass("d-none");
      }

      $conditionsTableBody.find('input[value="' + condition.id + '"]').remove();
    });

    if (!readonly) {
      $action = $("<div>").append($remove);

      var $moveUp = $("<a>")
        .attr("href", "#")
        .attr("role", "button")
        .append($("<span>").addClass("fa").addClass("fa-chevron-up"));
      $moveUp.click(function (e) {
        e.preventDefault(); // Prevent default action for the link
        if (!$row.prev().hasClass("default")) {
          $row.insertBefore($row.prev());
        }
      });

      var $moveDown = $("<a>")
        .attr("href", "#")
        .attr("role", "button")
        .append($("<span>").addClass("fa").addClass("fa-chevron-down"));
      $moveDown.click(function (e) {
        e.preventDefault(); // Prevent default action for the link
        $row.insertAfter($row.next());
      });

      $ordering = $("<div>")
        .css("text-align", "center")
        .append($moveUp)
        .append($("<hr>"))
        .append($moveDown);
    } else {
      $action = $("<div>");
      $ordering = $("<div>");
    }

    $row.append($("<td>").css("vertical-align", "middle").html($action));
    $row.append($("<td>").css("vertical-align", "middle").html($ordering));

    $conditionsTableBody.append($row);

    if (!readonly) {
      $row.append(
        $("<input>")
          .attr("type", "hidden")
          .attr("name", "conditionID")
          .val(condition.id)
      );
    }
  }

  function initDefaultConditions(defaultConditions) {
    $.each(defaultConditions, function (index, condition) {
      createConditionTableRow(condition, "default", true);
    });
  }

  function initAdditionalConditions(assessment) {
    var conditions = {},
      $searchConditions = $("#searchConditions"),
      $addCondition = $("#addCondition"),
      $conditionsForm = $("#conditionsForm");

    $searchConditions.select2({
      theme: "bootstrap-5",
      dropdownCssClass: "conditions-dropdown",
      minimumInputLength: 3,
      ajax: {
        url: "/applications/search-conditions",
        dataType: "json",
        quietMillis: 250,
        data: function (term, page) {
          return {
            q: term,
          };
        },
        results: function (data, page) {
          conditions = data;

          conditions = _.chain(data).keyBy("id").value();

          return { results: data };
        },
        cache: true,
      },
      formatResult: function (object) {
        var $container = $("<table>"),
          $row = $("<tr>");

        $row.append($("<td>").html(object.code));
        $row.append($("<td>").html(object.text));

        $container.append($row);

        return $container;
      },
      formatResultCssClass: function (object) {
        return "conditions-option";
      },
    });

    $searchConditions.on("change", function (e) {
      $addCondition.prop("disabled", false);
    });

    $addCondition.click(function (e) {
      var condition = conditions[$searchConditions.val()];
      existingConditions = $conditionsForm.find("input[type=hidden]");

      // only add condition if it hasn't already been entered
      if (
        !_.includes(
          _.map(existingConditions, function (condition) {
            return $(condition).val();
          }),
          String(condition.id),
          1
        )
      ) {
        createConditionTableRow(condition, "additional");
      } else {
        window.alert("The specified condition has already been entered.");
      }

      $searchConditions.select2("val", "");
    });

    $.each(assessment.conditions, function (index, condition) {
      createConditionTableRow(condition, "additional", false);
    });
  }

  function initForm() {
    $("#save, #conclude").click(function () {
      var $conditionsForm = $("#conditionsForm");

      if ($(this).attr("id") === "conclude") {
        $conditionsForm.append(
          $("<input>").attr("type", "hidden").attr("name", "conclude")
        );
      }

      $conditionsForm.submit();
    });
  }

  return {
    init: function (
      assessment,
      application,
      formStructure,
      otherAssessments,
      csrfToken,
      assessors,
      userID
    ) {
      initApplicationDetailsPopover(application, formStructure);
      initAssignee(assessment, csrfToken, assessors, userID);
      initOtherAssessorsCommentsPopover(otherAssessments);
      initDefaultConditions(application.licence_type.default_conditions);
      initAdditionalConditions(assessment);
      initForm();
    },
  };
});
