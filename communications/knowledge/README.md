# AI Assistant Knowledge Base

This directory contains knowledge base files that are automatically loaded and integrated into the AI Assistant's context.

## How It Works

1. **Automatic Loading**: All `.md` files in this directory are automatically loaded when the AI chat service starts
2. **Caching**: Knowledge base content is cached in memory for performance
3. **Integration**: The knowledge is included in the system prompt, allowing the AI to reference it when answering questions
4. **Hot Reload**: To reload knowledge after changes, restart the Django application

## Adding New Knowledge

To add new knowledge to the AI Assistant:

1. Create a new `.md` file in this directory (e.g., `TAX_COMPLIANCE_GUIDE.md`)
2. Write your content using clear markdown formatting
3. Use headings, tables, and lists for better organization
4. Include specific examples and common queries
5. Restart the Django application to load the new knowledge

## Knowledge File Structure

Each knowledge file should follow this structure:

```markdown
# Topic Title

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)

## Section 1
Content here...

## Section 2
Content here...

## Common Queries & Examples

### Q1: "Question here?"
**Answer:** Detailed answer...

### Q2: "Another question?"
**Answer:** Detailed answer...
```

## Best Practices

1. **Be Specific**: Include exact fees, timelines, form numbers, and procedures
2. **Use Examples**: Provide real-world examples and common scenarios
3. **Structure Well**: Use clear headings and tables for easy reference
4. **Keep Updated**: Review and update knowledge files regularly
5. **Include Sources**: Reference official sources and last update dates
6. **Add Q&A**: Include common questions with detailed answers

## Current Knowledge Files

- **BRS_KENYA_GUIDE.md**: Comprehensive guide to Business Registration Service Kenya
  - Entity registration procedures
  - Annual returns and compliance
  - Company maintenance
  - Document retrieval
  - Business linking
  - 2026 Smart Governance requirements

## Testing Knowledge Integration

To test if the AI is using the knowledge base:

1. Ask a specific question covered in the knowledge base
2. Verify the AI provides accurate information with specific details (fees, timelines, form numbers)
3. Check that the AI references the knowledge base content

Example test queries:
- "How do I register a private limited company in Kenya?"
- "What are the annual return requirements?"
- "How much does it cost to get a CR12?"
- "What is beneficial ownership and who must file?"

## Troubleshooting

**Knowledge not loading:**
- Check file permissions (files must be readable)
- Verify files are in `.md` format
- Check Django logs for loading errors
- Restart Django application

**AI not using knowledge:**
- Verify knowledge files contain content
- Check system prompt includes knowledge base
- Ensure knowledge is relevant to the query
- Review AI response for knowledge references

## Performance Considerations

- Knowledge base is loaded once and cached in memory
- Large knowledge bases may increase initial load time
- Consider splitting very large files into focused topics
- Monitor memory usage if adding many large files

## Future Enhancements

Potential improvements to the knowledge system:

1. **Semantic Search**: Use embeddings to find relevant knowledge sections
2. **Dynamic Loading**: Load only relevant knowledge based on query
3. **Version Control**: Track knowledge base versions and updates
4. **Admin Interface**: Web UI for managing knowledge files
5. **Analytics**: Track which knowledge sections are most used
6. **Multi-language**: Support knowledge in multiple languages

---

*For questions or issues with the knowledge base system, contact the development team.*
