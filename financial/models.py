"""
Financial models for Governance Hub
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Invoice(models.Model):
    """
    Invoice entity for tracking invoices (both receivable and payable).
    """
    
    INVOICE_TYPE_CHOICES = [
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='invoices',
        db_index=True
    )
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True)
    client_address = models.TextField(blank=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['company', 'invoice_type', 'status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"
    
    @property
    def is_paid(self):
        """Check if invoice is paid"""
        return self.status == 'paid'
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.status == 'overdue'
    
    def calculate_total(self):
        """Calculate total from subtotal and tax"""
        return self.subtotal + self.tax_amount


class InvoiceLineItem(models.Model):
    """
    Line items for invoices.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    class Meta:
        db_table = 'invoice_line_items'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Calculate amount before saving"""
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Expense(models.Model):
    """
    Expense entity for tracking company expenses.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_number = models.CharField(max_length=50, unique=True, db_index=True)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='expenses',
        db_index=True
    )
    employee = models.ForeignKey(
        'staff.Staff',
        on_delete=models.CASCADE,
        related_name='expenses',
        null=True,
        blank=True
    )
    category = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    expense_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    receipt_document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    approved_by = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['expense_number']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['employee']),
        ]
    
    def __str__(self):
        return f"{self.expense_number} - {self.category} - {self.amount}"
    
    @property
    def is_approved(self):
        """Check if expense is approved"""
        return self.status == 'approved'
    
    @property
    def is_paid(self):
        """Check if expense is paid"""
        return self.status == 'paid'


class PettyCashRequest(models.Model):
    """
    Petty cash request entity for tracking petty cash requests and disbursements.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='petty_cash_requests',
        db_index=True
    )
    requester = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='petty_cash_requests'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    purpose = models.TextField()
    request_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    approver = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_petty_cash'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    disbursement_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'petty_cash_requests'
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['requester']),
            models.Index(fields=['request_date']),
        ]
    
    def __str__(self):
        return f"Petty Cash Request - {self.requester.full_name} - {self.amount}"
    
    @property
    def is_approved(self):
        """Check if petty cash request is approved"""
        return self.status == 'approved'
    
    @property
    def is_disbursed(self):
        """Check if petty cash has been disbursed"""
        return self.status == 'disbursed'
    
    @property
    def is_pending(self):
        """Check if petty cash request is pending approval"""
        return self.status == 'pending'
