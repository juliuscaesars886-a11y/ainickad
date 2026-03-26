"""
Serializers for financial app
"""
from rest_framework import serializers
from .models import Invoice, InvoiceLineItem, Expense, PettyCashRequest
from decimal import Decimal


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice line items
    """
    class Meta:
        model = InvoiceLineItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount']
        read_only_fields = ['id', 'amount']


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing invoices (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    is_paid = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'status', 'client_name',
            'issue_date', 'due_date', 'total_amount', 'company_name',
            'is_paid', 'is_overdue', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice details (all fields with line items)
    """
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    is_paid = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'status', 'company',
            'client_name', 'client_email', 'client_address', 'issue_date',
            'due_date', 'paid_date', 'subtotal', 'tax_amount', 'total_amount',
            'notes', 'created_by', 'created_by_name', 'company_name',
            'line_items', 'is_paid', 'is_overdue', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating invoices with line items
    """
    line_items = InvoiceLineItemSerializer(many=True)
    
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'invoice_type', 'company', 'client_name',
            'client_email', 'client_address', 'issue_date', 'due_date',
            'subtotal', 'tax_amount', 'total_amount', 'notes', 'line_items', 'metadata'
        ]
    
    def validate_invoice_number(self, value):
        """Validate invoice number is unique"""
        if Invoice.objects.filter(invoice_number=value).exists():
            raise serializers.ValidationError(
                "An invoice with this invoice number already exists."
            )
        return value
    
    def validate(self, data):
        """Validate total calculation"""
        calculated_total = data['subtotal'] + data['tax_amount']
        if abs(calculated_total - data['total_amount']) > Decimal('0.01'):
            raise serializers.ValidationError({
                'total_amount': 'Total amount must equal subtotal + tax amount'
            })
        return data
    
    def create(self, validated_data):
        """Create invoice with line items"""
        line_items_data = validated_data.pop('line_items')
        invoice = Invoice.objects.create(**validated_data)
        
        for item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **item_data)
        
        return invoice


class InvoiceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating invoices
    """
    class Meta:
        model = Invoice
        fields = [
            'status', 'client_name', 'client_email', 'client_address',
            'due_date', 'paid_date', 'notes', 'metadata'
        ]


class ExpenseListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing expenses (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    is_approved = serializers.ReadOnlyField()
    is_paid = serializers.ReadOnlyField()
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number', 'category', 'description', 'amount',
            'expense_date', 'status', 'company_name', 'employee_name',
            'is_approved', 'is_paid', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for expense details (all fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    is_approved = serializers.ReadOnlyField()
    is_paid = serializers.ReadOnlyField()
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number', 'company', 'employee', 'category',
            'description', 'amount', 'expense_date', 'status',
            'receipt_document', 'approved_by', 'approved_by_name',
            'approved_at', 'notes', 'metadata', 'company_name',
            'employee_name', 'is_approved', 'is_paid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'approved_by', 'approved_at', 'created_at', 'updated_at']


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating expenses
    """
    class Meta:
        model = Expense
        fields = [
            'expense_number', 'company', 'employee', 'category',
            'description', 'amount', 'expense_date', 'receipt_document',
            'notes', 'metadata'
        ]
    
    def validate_expense_number(self, value):
        """Validate expense number is unique"""
        if Expense.objects.filter(expense_number=value).exists():
            raise serializers.ValidationError(
                "An expense with this expense number already exists."
            )
        return value
    
    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating expenses
    """
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount', 'expense_date',
            'receipt_document', 'notes', 'metadata'
        ]


class PettyCashRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing petty cash requests (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    is_approved = serializers.ReadOnlyField()
    is_disbursed = serializers.ReadOnlyField()
    is_pending = serializers.ReadOnlyField()
    
    class Meta:
        model = PettyCashRequest
        fields = [
            'id', 'company', 'company_name', 'requester', 'requester_name',
            'amount', 'purpose', 'request_date', 'status',
            'is_approved', 'is_disbursed', 'is_pending', 'created_at'
        ]
        read_only_fields = ['id', 'request_date', 'created_at']


class PettyCashRequestDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for petty cash request details (all fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    is_approved = serializers.ReadOnlyField()
    is_disbursed = serializers.ReadOnlyField()
    is_pending = serializers.ReadOnlyField()
    
    class Meta:
        model = PettyCashRequest
        fields = [
            'id', 'company', 'company_name', 'requester', 'requester_name',
            'amount', 'purpose', 'request_date', 'status', 'approver',
            'approver_name', 'approval_date', 'disbursement_date', 'notes',
            'metadata', 'is_approved', 'is_disbursed', 'is_pending',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'request_date', 'approver', 'approval_date',
            'disbursement_date', 'created_at', 'updated_at'
        ]


class PettyCashRequestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating petty cash requests
    """
    class Meta:
        model = PettyCashRequest
        fields = [
            'company', 'requester', 'amount', 'purpose', 'notes', 'metadata'
        ]
    
    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    
    def validate_purpose(self, value):
        """Validate purpose is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Purpose cannot be empty.")
        return value


class PettyCashRequestUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating petty cash requests
    """
    class Meta:
        model = PettyCashRequest
        fields = ['amount', 'purpose', 'notes', 'metadata']
