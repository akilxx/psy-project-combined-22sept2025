# reportgeneration/services.py

import logging
from .models import TestReport, ReportTemplate
from django.db import transaction
from django.db import IntegrityError

logger = logging.getLogger(__name__)


def generate_test_report(test_result, payment=None, ledger_entry=None):
    """
    Generates a TestReport for a given TestResult.
    Requires either a 'payment' or 'ledger_entry' as a funding source.
    """
    if not test_result:
        logger.error("generate_test_report called without a test_result.")
        return None

    if not (payment or ledger_entry):
        logger.error("generate_test_report called without a valid funding source.")
        return None

    psychometric_test = test_result.test

    # Retrieve the ReportTemplate
    try:
        report_template = psychometric_test.report_template
    except ReportTemplate.DoesNotExist:
        logger.error("No ReportTemplate found for PsychometricTest %s.", psychometric_test.id)
        return None

    if not test_result.percentiles:
        logger.error("TestResult %s has no calculated percentiles.", test_result.uuid)
        return None

    # Flatten percentiles from TestResult into a lookup dictionary
    percentiles_lookup = {}
    for entry in test_result.percentiles:
        trait_name = entry.get("trait")
        if trait_name:
            percentiles_lookup[trait_name] = entry.get("total_percentile")

        dims = entry.get("dimension_percentiles", {})
        for dim_name, dim_val in dims.items():
            percentiles_lookup[dim_name] = dim_val

    # Identify all expected traits/dimensions
    expected_traits = []
    for trait_def in psychometric_test.traits:
        t_name = trait_def['name']
        if t_name not in expected_traits:
            expected_traits.append(t_name)
        for d_name in trait_def.get('dimensions', []):
            if d_name not in expected_traits:
                expected_traits.append(d_name)

    # Build the report content
    report_entries = []
    all_blocks = list(report_template.content_blocks.all())

    for trait in expected_traits:
        percentile_value = percentiles_lookup.get(trait)

        if percentile_value is None:
            continue

        matched_content = ""
        for block in all_blocks:
            if block.trait == trait and \
                    block.percentile_lower_bound <= percentile_value <= block.percentile_upper_bound:
                matched_content = block.content
                break

        report_entries.append({
            "trait": trait,
            "percentile": percentile_value,
            "text": matched_content
        })

    # Create the TestReport
    try:
        with transaction.atomic():
            test_report = TestReport.objects.create(
                test_result=test_result,
                payment=payment,
                ledger_entry=ledger_entry,
                report_content=report_entries
            )
        logger.info("TestReport generated for Result %s.", test_result.uuid)
        return test_report

    except IntegrityError:
        # RACE CONDITION HANDLING
        # If we hit a unique constraint, it means the report was created
        # by another thread/process milliseconds ago.
        logger.warning(f"Race condition: Report for {test_result.uuid} already exists. Returning existing report.")
        return TestReport.objects.get(test_result=test_result)

    except Exception as e:
        logger.error("Failed to create TestReport for Result %s: %s", test_result.uuid, e)
        return None