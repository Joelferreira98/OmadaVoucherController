// CRUD Functions for Plans and Voucher Groups

// Plan Management Functions
function deletePlan(planId, planName) {
    if (confirm(`Tem certeza que deseja excluir o plano "${planName}"?\n\nEsta ação não pode ser desfeita.`)) {
        fetch(`/admin/plans/${planId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showAlert('success', data.message, 'check-circle');
                
                // Reload page to update the list
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                showAlert('danger', `Erro ao excluir plano: ${data.error}`, 'exclamation-triangle');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'Erro ao excluir plano. Tente novamente.', 'exclamation-triangle');
        });
    }
}

// Voucher Group Management Functions  
function deleteVoucherGroup(groupId, planName, quantity) {
    const groupInfo = `${planName} (${quantity} vouchers)`;
    if (confirm(`Tem certeza que deseja excluir o grupo de vouchers:\n${groupInfo}\n\nEsta ação remove os vouchers do Omada Controller e não pode ser desfeita.`)) {
        fetch(`/admin/vouchers/${groupId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message, 'check-circle');
                
                // Remove the selected row's checkbox if checked
                const checkbox = document.querySelector(`input[value="${groupId}"]`);
                if (checkbox) {
                    checkbox.checked = false;
                    updateDeleteButton();
                }
                
                // Reload page to update the list
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                showAlert('danger', `Erro ao excluir vouchers: ${data.error}`, 'exclamation-triangle');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'Erro ao excluir vouchers. Tente novamente.', 'exclamation-triangle');
        });
    }
}

// Utility Functions
function showAlert(type, message, icon) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    const firstRow = container.querySelector('.row');
    if (firstRow) {
        container.insertBefore(alertDiv, firstRow);
    } else {
        container.appendChild(alertDiv);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Initialize functions when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Any initialization code can go here
    console.log('CRUD functions loaded');
});