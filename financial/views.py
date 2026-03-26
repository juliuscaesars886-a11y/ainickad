"""
Views for financial app
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import Invoice, Expense, PettyCashRequest
from .serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    InvoiceUpdateSerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    ExpenseCreateSerializer,
    ExpenseUpdateSerializer,
    PettyCashRequestListSerializer,
    PettyCashRequestDetailSerializer,
    PettyCashRequestCreateSerializer,
    PettyCashRequestUpdateSerializer
)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Invoice CRUD operations.
    
    Endpoints:
    - GET /api/invoices/ - List invoices (filtered by company)
    - POST /api/invoices/ - Create invoice
    - GET /api/invoices/{id}/ - Get invoice details
    - PATCH /api/invoices/{id}/ - Update invoice
    - DELETE /api/invoices/{id}/ - Delete invoice
    - POST /api/invoices/{id}/mark-paid/ - Mark invoice as paid
    """
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['invoice_type', 'status', 'company']
    search_fields = ['invoice_number', 'client_name', 'client_email']
    ordering_fields = ['issue_date', 'due_date', 'total_amount', 'created_at']
    ordering = ['-issue_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return InvoiceUpdateSerializer
        return InvoiceDetailSerializer
    
    def get_queryset(self):
        """
        Return all invoices - no company-based filtering.
        All authenticated users can view all invoices.
        """
        return Invoice.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new invoice (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can create invoices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Non-super admins can only create invoices for their own company
        if not request.user.is_super_admin:
            company_id = serializer.validated_data.get('company').id
            if company_id != request.user.company.id:
                return Response(
                    {'error': 'You can only create invoices for your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        invoice = serializer.save(created_by=request.user)
        
        # Return detailed serializer
        detail_serializer = InvoiceDetailSerializer(invoice)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update an invoice (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can update invoices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Non-super admins can only update invoices from their own company
        if not request.user.is_super_admin and instance.company.id != request.user.company.id:
            return Response(
                {'error': 'You can only update invoices from your own company'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        
        # Return detailed serializer
        detail_serializer = InvoiceDetailSerializer(invoice)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete an invoice (admin or super_admin only)
        """
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can delete invoices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        
        # Non-super admins can only delete invoices from their own company
        if not request.user.is_super_admin and instance.company.id != request.user.company.id:
            return Response(
                {'error': 'You can only delete invoices from your own company'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Don't allow deleting paid invoices
        if instance.status == 'paid':
            return Response(
                {'error': 'Cannot delete paid invoices'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """
        Mark an invoice as paid
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can mark invoices as paid'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        invoice = self.get_object()
        
        if invoice.status == 'paid':
            return Response(
                {'error': 'Invoice is already marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'paid'
        invoice.paid_date = timezone.now().date()
        invoice.save()
        
        serializer = InvoiceDetailSerializer(invoice)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Expense CRUD operations.
    
    Endpoints:
    - GET /api/expenses/ - List expenses (filtered by company)
    - POST /api/expenses/ - Create expense
    - GET /api/expenses/{id}/ - Get expense details
    - PATCH /api/expenses/{id}/ - Update expense
    - DELETE /api/expenses/{id}/ - Delete expense
    - POST /api/expenses/{id}/approve/ - Approve expense
    - POST /api/expenses/{id}/reject/ - Reject expense
    """
    queryset = Expense.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'category', 'company', 'employee']
    search_fields = ['expense_number', 'description', 'category']
    ordering_fields = ['expense_date', 'amount', 'created_at']
    ordering = ['-expense_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ExpenseListSerializer
        elif self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExpenseUpdateSerializer
        return ExpenseDetailSerializer
    
    def get_queryset(self):
        """
        Return all expenses - no company-based filtering.
        All authenticated users can view all expenses.
        """
        return Expense.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new expense
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Non-super admins can only create expenses for their own company
        if not request.user.is_super_admin:
            company_id = serializer.validated_data.get('company').id
            if company_id != request.user.company.id:
                return Response(
                    {'error': 'You can only create expenses for your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        expense = serializer.save()
        
        # Return detailed serializer
        detail_serializer = ExpenseDetailSerializer(expense)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update an expense (only if pending)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only pending expenses can be updated
        if instance.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be updated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Non-accountants can only update their own expenses
        if not request.user.is_accountant:
            try:
                if instance.employee != request.user.employee:
                    return Response(
                        {'error': 'You can only update your own expenses'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except:
                return Response(
                    {'error': 'You do not have an employee profile'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        
        # Return detailed serializer
        detail_serializer = ExpenseDetailSerializer(expense)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete an expense (only if pending)
        """
        instance = self.get_object()
        
        # Only pending expenses can be deleted
        if instance.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Non-accountants can only delete their own expenses
        if not request.user.is_accountant:
            try:
                if instance.employee != request.user.employee:
                    return Response(
                        {'error': 'You can only delete your own expenses'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except:
                return Response(
                    {'error': 'You do not have an employee profile'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve an expense (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can approve expenses'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        expense = self.get_object()
        
        if expense.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'approved'
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save()
        
        serializer = ExpenseDetailSerializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject an expense (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can reject expenses'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        expense = self.get_object()
        
        if expense.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'rejected'
        expense.save()
        
        serializer = ExpenseDetailSerializer(expense)
        return Response(serializer.data)



class PettyCashRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PettyCashRequest CRUD operations.
    
    Endpoints:
    - GET /api/petty-cash/ - List petty cash requests (filtered by company)
    - POST /api/petty-cash/ - Create petty cash request
    - GET /api/petty-cash/{id}/ - Get petty cash details
    - PATCH /api/petty-cash/{id}/ - Update petty cash request
    - DELETE /api/petty-cash/{id}/ - Delete petty cash request
    - POST /api/petty-cash/{id}/approve/ - Approve petty cash request
    - POST /api/petty-cash/{id}/reject/ - Reject petty cash request
    - POST /api/petty-cash/{id}/disburse/ - Mark petty cash as disbursed
    """
    queryset = PettyCashRequest.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'company', 'requester']
    search_fields = ['purpose', 'notes']
    ordering_fields = ['request_date', 'amount', 'created_at']
    ordering = ['-request_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return PettyCashRequestListSerializer
        elif self.action == 'create':
            return PettyCashRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PettyCashRequestUpdateSerializer
        return PettyCashRequestDetailSerializer
    
    def get_queryset(self):
        """
        Filter petty cash requests based on user role.
        
        - Super admins see all requests
        - Accountants and admins see requests from their company
        - Employees see only their own requests
        """
        user = self.request.user
        
        if user.is_super_admin:
            return PettyCashRequest.objects.all()
        elif user.is_accountant:
            return PettyCashRequest.objects.filter(company=user.company)
        elif user.company:
            # Employees see only their own requests
            return PettyCashRequest.objects.filter(requester=user)
        else:
            return PettyCashRequest.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new petty cash request
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Non-super admins can only create requests for their own company
        if not request.user.is_super_admin:
            company_id = serializer.validated_data.get('company').id
            if company_id != request.user.company.id:
                return Response(
                    {'error': 'You can only create petty cash requests for your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Ensure requester is the current user (unless super admin)
        if not request.user.is_super_admin:
            requester_id = serializer.validated_data.get('requester').id
            if requester_id != request.user.id:
                return Response(
                    {'error': 'You can only create petty cash requests for yourself'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        petty_cash = serializer.save()
        
        # Return detailed serializer
        detail_serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update a petty cash request (only if draft or pending)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only draft or pending requests can be updated
        if instance.status not in ['draft', 'pending']:
            return Response(
                {'error': 'Only draft or pending petty cash requests can be updated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Non-accountants can only update their own requests
        if not request.user.is_accountant:
            if instance.requester != request.user:
                return Response(
                    {'error': 'You can only update your own petty cash requests'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        petty_cash = serializer.save()
        
        # Return detailed serializer
        detail_serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a petty cash request (only if draft)
        """
        instance = self.get_object()
        
        # Only draft requests can be deleted
        if instance.status != 'draft':
            return Response(
                {'error': 'Only draft petty cash requests can be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Non-accountants can only delete their own requests
        if not request.user.is_accountant:
            if instance.requester != request.user:
                return Response(
                    {'error': 'You can only delete your own petty cash requests'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a petty cash request (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can approve petty cash requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        petty_cash = self.get_object()
        
        if petty_cash.status != 'pending':
            return Response(
                {'error': 'Only pending petty cash requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        petty_cash.status = 'approved'
        petty_cash.approver = request.user
        petty_cash.approval_date = timezone.now()
        petty_cash.save()
        
        serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a petty cash request for approval (changes status from draft to pending)
        """
        petty_cash = self.get_object()
        
        # Only the requester can submit their own request (unless accountant/admin)
        if not request.user.is_accountant and petty_cash.requester != request.user:
            return Response(
                {'error': 'You can only submit your own petty cash requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if petty_cash.status != 'draft':
            return Response(
                {'error': 'Only draft petty cash requests can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Change status to pending to initiate approval workflow
        petty_cash.status = 'pending'
        petty_cash.save()
        
        # TODO: Create notification for accountants/admins about pending approval
        # This will be implemented when the notification system is added
        
        serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a petty cash request (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can reject petty cash requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        petty_cash = self.get_object()
        
        if petty_cash.status != 'pending':
            return Response(
                {'error': 'Only pending petty cash requests can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        petty_cash.status = 'rejected'
        petty_cash.save()
        
        serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """
        Mark a petty cash request as disbursed (accountant, admin, or super_admin only)
        """
        if not request.user.is_accountant:
            return Response(
                {'error': 'Only accountants and admins can disburse petty cash'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        petty_cash = self.get_object()
        
        if petty_cash.status != 'approved':
            return Response(
                {'error': 'Only approved petty cash requests can be disbursed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        petty_cash.status = 'disbursed'
        petty_cash.disbursement_date = timezone.now()
        petty_cash.save()
        
        serializer = PettyCashRequestDetailSerializer(petty_cash)
        return Response(serializer.data)
