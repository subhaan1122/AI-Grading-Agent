import streamlit as st
import pandas as pd
import os
import asyncio
from typing import List, Dict, Any
import time
from io import BytesIO

from file_processor import FileProcessor
from ocr_service import OCRService
from grading_service import GradingService
from excel_export import ExcelExporter
from helpers import validate_file_type, format_grade_display

# Page configuration
st.set_page_config(
    page_title="AI Grading System",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize services
@st.cache_resource
def initialize_services():
    """Initialize all services with API keys from environment"""
    return {
        'file_processor': FileProcessor(),
        'ocr_service': OCRService(),
        'grading_service': GradingService(),
        'excel_exporter': ExcelExporter()
    }


def main():
    st.title("🎓 AI-Powered Grading System")
    st.markdown("Upload assignments and exams to get automated grading with detailed feedback")

    # Initialize services
    services = initialize_services()

    # Sidebar for configuration
    with st.sidebar:
        st.header("📋 Grading Configuration")

        # Total marks configuration
        total_marks = st.number_input(
            "Total Marks for Assignment",
            min_value=1,
            max_value=1000,
            value=100,
            help="Enter the total marks for this assignment"
        )

        # Custom grading criteria
        st.subheader("🎯 Custom Grading Criteria")

        # Option to use custom criteria
        use_custom_criteria = st.checkbox(
            "Use Custom Grading Criteria",
            help="Define specific point allocation for different aspects"
        )

        custom_criteria = {}
        if use_custom_criteria:
            st.write("Define your grading criteria:")

            # Dynamic criteria input
            num_criteria = st.number_input("Number of Criteria", min_value=1, max_value=10, value=3)

            for i in range(int(num_criteria)):
                col1, col2 = st.columns([2, 1])
                with col1:
                    criterion_name = st.text_input(
                        f"Criterion {i + 1}",
                        value=f"Criterion {i + 1}",
                        key=f"criterion_name_{i}"
                    )
                with col2:
                    criterion_marks = st.number_input(
                        "Marks",
                        min_value=0,
                        max_value=total_marks,
                        value=10,
                        key=f"criterion_marks_{i}"
                    )

                if criterion_name:
                    custom_criteria[criterion_name] = criterion_marks

            # Validate that custom criteria don't exceed total marks
            if sum(custom_criteria.values()) > total_marks:
                st.error(
                    f"⚠️ Sum of criteria marks ({sum(custom_criteria.values())}) exceeds total marks ({total_marks})")

        # Additional instructions
        additional_instructions = st.text_area(
            "Additional Grading Instructions",
            placeholder="Enter any specific instructions for grading...",
            help="Provide context about the assignment, what to look for, etc."
        )

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📁 Upload Assignment Files")

        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files to grade",
            type=['pdf', 'docx', 'jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help="Supported formats: PDF, Word documents, and images (JPG, PNG)"
        )

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully")

            # Display uploaded files
            with st.expander("📄 Uploaded Files", expanded=True):
                for file in uploaded_files:
                    file_type = validate_file_type(file.name)
                    file_type_display = file_type.upper() if file_type else "UNKNOWN"
                    st.write(f"• **{file.name}** ({file_type_display}) - {file.size:,} bytes")

    with col2:
        st.header("⚙️ Processing Options")

        # Multi-question detection
        detect_multiple_questions = st.checkbox(
            "Detect Multiple Questions",
            value=True,
            help="Attempt to identify and grade multiple questions within each file"
        )

        # Export options
        st.subheader("📊 Export Options")
        export_to_excel = st.checkbox(
            "Export Results to Excel",
            value=True,
            help="Compile all results into an Excel file"
        )

        show_detailed_feedback = st.checkbox(
            "Show Detailed Feedback",
            value=True,
            help="Display comprehensive feedback for each submission"
        )

    # Processing section
    if uploaded_files:
        st.header("🚀 Start Grading")

        if st.button("Grade All Assignments", type="primary", use_container_width=True):
            # Validate configuration
            if use_custom_criteria and sum(custom_criteria.values()) > total_marks:
                st.error("Please fix the grading criteria configuration before proceeding.")
                return

            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()

            all_results = []

            try:
                for idx, uploaded_file in enumerate(uploaded_files):
                    # Update progress
                    progress = (idx) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {uploaded_file.name}...")

                    # Process individual file
                    with st.spinner(f"Grading {uploaded_file.name}..."):
                        result = process_single_file(
                            uploaded_file,
                            services,
                            total_marks,
                            custom_criteria if use_custom_criteria else {},
                            additional_instructions,
                            detect_multiple_questions
                        )

                        if result:
                            all_results.append(result)

                # Complete progress
                progress_bar.progress(1.0)
                status_text.text("✅ All files processed successfully!")

                # Display results
                if all_results:
                    display_results(all_results, show_detailed_feedback, results_container)

                    # Export to Excel if requested
                    if export_to_excel and all_results:
                        excel_data = services['excel_exporter'].create_excel_report(all_results)
                        if excel_data:
                            st.download_button(
                                label="📥 Download Excel Report",
                                data=excel_data,
                                file_name=f"grading_report_{int(time.time())}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

            except Exception as e:
                st.error(f"❌ Error during processing: {str(e)}")
                st.exception(e)


def process_single_file(uploaded_file, services, total_marks, custom_criteria, additional_instructions,
                        detect_multiple_questions) -> Dict[str, Any]:
    """Process a single uploaded file and return grading results"""
    file_type = validate_file_type(uploaded_file.name)

    try:

        # Extract text content
        if file_type in ['jpg', 'jpeg', 'png']:
            # Use OCR for images
            text_content = services['ocr_service'].extract_text_from_image(uploaded_file)
        else:
            # Use file processor for PDF/DOCX
            text_content = services['file_processor'].extract_text(uploaded_file, file_type)

        if not text_content or not text_content.strip():
            st.warning(f"⚠️ No text content found in {uploaded_file.name}")
            return {
                'filename': uploaded_file.name,
                'file_type': file_type or 'unknown',
                'total_marks': total_marks,
                'awarded_marks': 0,
                'percentage': 0,
                'feedback': 'No text content could be extracted from this file.',
                'criteria_breakdown': {},
                'questions': [],
                'text_content': 'No content available'
            }

        # Grade the content
        grading_result = services['grading_service'].grade_assignment(
            text_content,
            total_marks,
            custom_criteria,
            additional_instructions,
            detect_multiple_questions
        )

        # Prepare result object
        result = {
            'filename': uploaded_file.name,
            'file_type': file_type,
            'total_marks': total_marks,
            'awarded_marks': grading_result.get('total_score', 0),
            'percentage': (grading_result.get('total_score', 0) / total_marks) * 100,
            'feedback': grading_result.get('feedback', ''),
            'criteria_breakdown': grading_result.get('criteria_scores', {}),
            'questions': grading_result.get('questions', []),
            'text_content': text_content[:500] + "..." if len(text_content) > 500 else text_content
        }

        return result

    except Exception as e:
        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        return {
            'filename': uploaded_file.name,
            'file_type': file_type or 'unknown',
            'total_marks': total_marks,
            'awarded_marks': 0,
            'percentage': 0,
            'feedback': f'Error processing file: {str(e)}',
            'criteria_breakdown': {},
            'questions': [],
            'text_content': 'Error occurred during processing'
        }


def display_results(results: List[Dict], show_detailed_feedback: bool, container):
    """Display grading results in an organized format"""
    with container:
        st.header("📊 Grading Results")

        # Summary statistics
        total_files = len(results)
        avg_score = sum(r['percentage'] for r in results) / total_files if results else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files Graded", total_files)
        with col2:
            st.metric("Average Score", f"{avg_score:.1f}%")
        with col3:
            highest_score = max(r['percentage'] for r in results) if results else 0
            st.metric("Highest Score", f"{highest_score:.1f}%")

        # Results table
        st.subheader("📋 Summary Table")

        # Create DataFrame for display
        df_data = []
        for result in results:
            df_data.append({
                'File Name': result['filename'],
                'Score': f"{result['awarded_marks']}/{result['total_marks']}",
                'Percentage': f"{result['percentage']:.1f}%",
                'Grade': format_grade_display(result['percentage'])
            })

        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

        # Detailed results for each file
        st.subheader("📝 Detailed Results")

        for result in results:
            with st.expander(
                    f"📄 {result['filename']} - {result['awarded_marks']}/{result['total_marks']} ({result['percentage']:.1f}%)"):

                # Score breakdown
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.write("**Score Breakdown:**")
                    if result['criteria_breakdown']:
                        for criterion, score in result['criteria_breakdown'].items():
                            st.write(f"• {criterion}: {score}")
                    else:
                        st.write(f"Total Score: {result['awarded_marks']}/{result['total_marks']}")

                with col2:
                    st.write("**File Information:**")
                    st.write(f"• File Type: {result['file_type'].upper()}")
                    st.write(f"• Grade: {format_grade_display(result['percentage'])}")

                # Questions breakdown (if multiple questions detected)
                if result['questions'] and len(result['questions']) > 1:
                    st.write("**Questions Breakdown:**")
                    for i, question in enumerate(result['questions'], 1):
                        st.write(f"**Question {i}:** {question.get('score', 0)} marks")
                        if show_detailed_feedback and question.get('feedback'):
                            st.write(f"*Feedback:* {question['feedback']}")

                # Overall feedback
                if show_detailed_feedback and result['feedback']:
                    st.write("**Overall Feedback:**")
                    st.write(result['feedback'])

                # Text content preview - moved outside of expander
                st.write("**Extracted Text Preview:**")
                st.text_area("Text Content", value=result['text_content'], height=100, disabled=True,
                             key=f"text_preview_{result['filename']}")


if __name__ == "__main__":
    main()
