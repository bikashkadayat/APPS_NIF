import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Pencil, UserPlus, RotateCcw, Repeat } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useAutoRefresh } from '../../hooks/useAutoRefresh';
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock';
import { inventoryService } from '../../services/inventoryService';

const STATUS_COLORS = {
  available: '#065f46', assigned: '#1e40af', out: '#b45309',
  maintenance: '#6b21a8', retired: '#6b7280',
};
const StatusPill = ({ value, label }) => (
  <span style={{
    display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontSize: 12,
    fontWeight: 600, color: '#fff', background: STATUS_COLORS[value] || '#6b7280',
  }}>{label || value}</span>
);

const MANAGER_ROLES = ['admin', 'approver', 'checker'];
const CONDITIONS = [['new', 'New'], ['good', 'Good'], ['fair', 'Fair'], ['damaged', 'Damaged']];
const ASSET_TYPES = [['it', 'IT / Computing'], ['peripheral', 'Peripheral'], ['furniture', 'Furniture'], ['vehicle', 'Vehicle'], ['other', 'Other']];
const IT_TYPES = ['it', 'peripheral'];
const today = () => new Date().toISOString().slice(0, 10);

const emptyItem = {
  name: '', asset_type: 'it', category: '', serial_number: '', condition: 'good',
  purchase_date: '', notes: '', status: 'available',
  brand: '', model: '', cpu: '', ram: '', storage_type: '', storage_size: '',
  gpu: '', screen_size: '', os: '', mac_address: '', ip_address: '',
  warranty_expiry: '', purchase_cost: '', vendor: '', accessories: '',
};

// Searchable native employee <select> (text filter above the list).
const EmployeePicker = ({ employees, value, onChange }) => {
  const [q, setQ] = useState('');
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? employees.filter(u => `${u.full_name} ${u.employee_id || ''}`.toLowerCase().includes(s)) : employees;
  }, [q, employees]);
  return (
    <>
      <input placeholder="Search employee…" value={q} onChange={e => setQ(e.target.value)} style={{ marginBottom: 8 }} />
      <select value={value} onChange={e => onChange(e.target.value)}>
        <option value="">— Select employee —</option>
        {filtered.map(u => <option key={u.id} value={u.id}>{u.full_name}{u.employee_id ? ` (${u.employee_id})` : ''}</option>)}
      </select>
    </>
  );
};

const InventoryList = () => {
  const navigate = useNavigate();
  const { role } = useAuth();
  const isManager = MANAGER_ROLES.includes(role);

  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [popup, setPopup] = useState(null);

  const [editItem, setEditItem] = useState(null);
  const [assignCtx, setAssignCtx] = useState(null);   // { item, mode: 'assign'|'handover' }
  const [assignForm, setAssignForm] = useState({ assigned_to: '', assigned_date: today(), handover_condition: 'good', accessories: '', note: '' });
  const [returnCtx, setReturnCtx] = useState(null);
  const [returnForm, setReturnForm] = useState({ return_condition: 'good', return_remarks: '' });
  const [saving, setSaving] = useState(false);
  useBodyScrollLock(!!(editItem || assignCtx || returnCtx || popup));

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = statusFilter === 'all' ? {} : { status: statusFilter };
      const [it, cats] = await Promise.all([inventoryService.items(params), inventoryService.categories()]);
      setItems(it); setCategories(cats);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load inventory.');
    } finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);
  useAutoRefresh(load, 30000);
  useEffect(() => { if (isManager) inventoryService.employees().then(setEmployees).catch(() => {}); }, [isManager]);

  const saveItem = async () => {
    setSaving(true);
    try {
      const payload = { ...editItem };
      ['category', 'purchase_date', 'warranty_expiry', 'ip_address', 'purchase_cost'].forEach(k => { if (!payload[k]) delete payload[k]; });
      if (editItem.id) await inventoryService.updateItem(editItem.id, payload);
      else await inventoryService.createItem(payload);
      setEditItem(null); await load();
      setPopup({ type: 'success', msg: editItem.id ? 'Item updated.' : 'Item added.' });
    } catch (e) {
      setPopup({ type: 'error', msg: e?.response?.data?.detail || 'Could not save the item.' });
    } finally { setSaving(false); }
  };

  const openAssign = (item, mode) => {
    setAssignForm({ assigned_to: '', assigned_date: today(), handover_condition: item.condition || 'good', accessories: item.accessories || '', note: '' });
    setAssignCtx({ item, mode });
  };

  const doAssign = async () => {
    if (!assignForm.assigned_to) return;
    setSaving(true);
    try {
      const fn = assignCtx.mode === 'handover' ? inventoryService.handoverItem : inventoryService.assignItem;
      await fn(assignCtx.item.id, assignForm);
      setAssignCtx(null); await load();
      setPopup({ type: 'success', msg: assignCtx.mode === 'handover' ? 'Item handed over.' : 'Item assigned.' });
    } catch (e) {
      setPopup({ type: 'error', msg: e?.response?.data?.detail || 'Could not complete the action.' });
    } finally { setSaving(false); }
  };

  const doReturn = async () => {
    setSaving(true);
    try {
      await inventoryService.returnItem(returnCtx.id, returnForm);
      setReturnCtx(null); await load();
      setPopup({ type: 'success', msg: 'Item returned to stock.' });
    } catch (e) {
      setPopup({ type: 'error', msg: e?.response?.data?.detail || 'Could not return the item.' });
    } finally { setSaving(false); }
  };

  const filters = ['all', 'available', 'assigned', 'out', 'maintenance', 'retired'];
  const showSpecs = IT_TYPES.includes(editItem?.asset_type);

  return (
    <div className="page">
      {popup && (
        <div className="popup-overlay" onClick={() => setPopup(null)}>
          <div className="popup-modal" onClick={e => e.stopPropagation()}>
            <h3>{popup.type === 'success' ? 'Done' : 'Error'}</h3>
            <p>{popup.msg}</p>
            <button className="popup-btn" onClick={() => setPopup(null)}>OK</button>
          </div>
        </div>
      )}

      <div className="pg-head">
        <div className="pg-head-left">
          <div className="pg-breadcrumb">
            <button className="pg-back" onClick={() => navigate('/')}><ArrowLeft size={18} /></button>
            Inventory
          </div>
          <div className="pg-title">Inventory Items</div>
          <div className="pg-desc">Office assets and who is currently using each one</div>
        </div>
        {isManager && (
          <div className="pg-head-right">
            <button className="btn btn-primary" onClick={() => setEditItem({ ...emptyItem })}><Plus size={16} /> Add Item</button>
          </div>
        )}
      </div>

      <div className="table-card">
        <div className="tc-top">
          <span className="tc-title">Items</span>
          <div className="filter-row">
            {filters.map(f => (
              <button key={f} className={`ftag ${statusFilter === f ? 'on' : ''}`} onClick={() => setStatusFilter(f)}>
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>Loading inventory…</div>
        ) : error ? (
          <div style={{ padding: 32, textAlign: 'center' }}>
            <div style={{ color: 'var(--danger, #b91c1c)', marginBottom: 12 }}>{error}</div>
            <button className="btn btn-primary" onClick={load}>Retry</button>
          </div>
        ) : (
          <div className="resp-table-wrap">
            <table className="resp-table">
              <thead>
                <tr>
                  <th>Asset Code</th><th>Item</th><th>Category</th>
                  <th>Status</th><th>Current Holder</th>{isManager && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.id}>
                    <td data-label="Asset Code">
                      <button onClick={() => navigate(`/inventory/items/${it.id}`)}
                        style={{ fontWeight: 700, color: 'var(--brand-blue)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline', font: 'inherit' }}>
                        {it.asset_code}
                      </button>
                    </td>
                    <td data-label="Item">
                      <div>{it.name}</div>
                      <div className="leave-meta" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {it.asset_type_display}{it.brand ? ` · ${it.brand} ${it.model}` : ''}{it.serial_number ? ` · SN ${it.serial_number}` : ''}
                      </div>
                    </td>
                    <td data-label="Category">{it.category_name || '—'}</td>
                    <td data-label="Status"><StatusPill value={it.status} label={it.status_display} /></td>
                    <td data-label="Holder">
                      {it.current_holder
                        ? <div>{it.current_holder}<div className="leave-meta" style={{ fontSize: 12, color: 'var(--text-muted)' }}>since {it.assigned_date_bs || it.assigned_date || '—'}</div></div>
                        : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    {isManager && (
                      <td data-label="Actions">
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                          <button className="btn btn-ghost btn-sm" title="Edit" onClick={() => setEditItem({
                            ...emptyItem, ...it, category: it.category || '',
                            purchase_date: it.purchase_date || '', warranty_expiry: it.warranty_expiry || '',
                            ip_address: it.ip_address || '', purchase_cost: it.purchase_cost ?? '',
                          })}><Pencil size={14} /></button>
                          {['available', 'assigned'].includes(it.status) && (
                            <button className="btn btn-ghost btn-sm" title="Assign" onClick={() => openAssign(it, 'assign')}><UserPlus size={14} /></button>
                          )}
                          {['assigned', 'out'].includes(it.status) && (
                            <button className="btn btn-ghost btn-sm" title="Handover" onClick={() => openAssign(it, 'handover')}><Repeat size={14} /></button>
                          )}
                          {['assigned', 'out'].includes(it.status) && (
                            <button className="btn btn-ghost btn-sm" title="Return" onClick={() => { setReturnForm({ return_condition: it.condition || 'good', return_remarks: '' }); setReturnCtx(it); }}><RotateCcw size={14} /></button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr><td colSpan={isManager ? 6 : 5} style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>No items yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit modal */}
      {editItem && (
        <div className="modal-overlay" onClick={() => !saving && setEditItem(null)}>
          <div className="modal-content" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 20px', fontSize: 18 }}>{editItem.id ? 'Edit Item' : 'Add Item'}</h3>
            <div className="fgrid">
              <div className="fg"><label>Name <span className="req">*</span></label>
                <input value={editItem.name} placeholder="e.g. Dell Latitude 5540" onChange={e => setEditItem({ ...editItem, name: e.target.value })} /></div>
              <div className="fg"><label>Asset Type</label>
                <select value={editItem.asset_type} onChange={e => setEditItem({ ...editItem, asset_type: e.target.value })}>
                  {ASSET_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></div>
            </div>
            <div className="fgrid">
              <div className="fg"><label>Category <span className="req">*</span></label>
                <select value={editItem.category || ''} onChange={e => setEditItem({ ...editItem, category: e.target.value })}>
                  <option value="">— Select category —</option>
                  {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select></div>
              <div className="fg"><label>Serial Number</label>
                <input value={editItem.serial_number} placeholder="Optional" onChange={e => setEditItem({ ...editItem, serial_number: e.target.value })} /></div>
            </div>
            <div className="fgrid">
              <div className="fg"><label>Condition</label>
                <select value={editItem.condition} onChange={e => setEditItem({ ...editItem, condition: e.target.value })}>
                  {CONDITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></div>
              <div className="fg"><label>Status</label>
                <select value={editItem.status} onChange={e => setEditItem({ ...editItem, status: e.target.value })}>
                  {['available', 'assigned', 'out', 'maintenance', 'retired'].map(s => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
                </select></div>
            </div>
            <div className="fgrid">
              <div className="fg"><label>Purchase Date</label>
                <input type="date" value={editItem.purchase_date || ''} onChange={e => setEditItem({ ...editItem, purchase_date: e.target.value })} /></div>
              <div className="fg"><label>Vendor / Supplier</label>
                <input value={editItem.vendor} onChange={e => setEditItem({ ...editItem, vendor: e.target.value })} /></div>
            </div>

            {showSpecs && (
              <>
                <div className="fsec" style={{ margin: '8px 0 16px' }}>Device Specifications</div>
                <div className="fgrid">
                  <div className="fg"><label>Brand</label><input value={editItem.brand} onChange={e => setEditItem({ ...editItem, brand: e.target.value })} /></div>
                  <div className="fg"><label>Model</label><input value={editItem.model} onChange={e => setEditItem({ ...editItem, model: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>CPU</label><input value={editItem.cpu} placeholder="e.g. Intel i7-1355U" onChange={e => setEditItem({ ...editItem, cpu: e.target.value })} /></div>
                  <div className="fg"><label>RAM</label><input value={editItem.ram} placeholder="e.g. 16GB" onChange={e => setEditItem({ ...editItem, ram: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>Storage Type</label><input value={editItem.storage_type} placeholder="SSD / HDD / NVMe" onChange={e => setEditItem({ ...editItem, storage_type: e.target.value })} /></div>
                  <div className="fg"><label>Storage Size</label><input value={editItem.storage_size} placeholder="e.g. 512GB" onChange={e => setEditItem({ ...editItem, storage_size: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>GPU</label><input value={editItem.gpu} onChange={e => setEditItem({ ...editItem, gpu: e.target.value })} /></div>
                  <div className="fg"><label>Screen Size</label><input value={editItem.screen_size} placeholder='e.g. 15.6"' onChange={e => setEditItem({ ...editItem, screen_size: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>Operating System</label><input value={editItem.os} onChange={e => setEditItem({ ...editItem, os: e.target.value })} /></div>
                  <div className="fg"><label>Accessories</label><input value={editItem.accessories} placeholder="Charger, Bag, Mouse" onChange={e => setEditItem({ ...editItem, accessories: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>MAC Address</label><input value={editItem.mac_address} onChange={e => setEditItem({ ...editItem, mac_address: e.target.value })} /></div>
                  <div className="fg"><label>IP Address</label><input value={editItem.ip_address} placeholder="Optional" onChange={e => setEditItem({ ...editItem, ip_address: e.target.value })} /></div>
                </div>
                <div className="fgrid">
                  <div className="fg"><label>Warranty Expiry</label><input type="date" value={editItem.warranty_expiry || ''} onChange={e => setEditItem({ ...editItem, warranty_expiry: e.target.value })} /></div>
                  <div className="fg"><label>Purchase Cost</label><input type="number" step="0.01" value={editItem.purchase_cost} onChange={e => setEditItem({ ...editItem, purchase_cost: e.target.value })} /></div>
                </div>
              </>
            )}

            <div className="fg"><label>Notes</label>
              <textarea rows={2} style={{ minHeight: 72 }} value={editItem.notes} onChange={e => setEditItem({ ...editItem, notes: e.target.value })} /></div>
            {!editItem.category && editItem.name && (
              <div style={{ color: 'var(--brand-red)', fontSize: 13, marginBottom: 12 }}>Category is required.</div>
            )}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" disabled={saving} onClick={() => setEditItem(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={saving || !editItem.name.trim() || !editItem.category} onClick={saveItem}>{saving ? 'Saving…' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Assign / Handover modal */}
      {assignCtx && (
        <div className="modal-overlay" onClick={() => !saving && setAssignCtx(null)}>
          <div className="modal-content" style={{ maxWidth: 520 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 4px', fontSize: 18 }}>{assignCtx.mode === 'handover' ? 'Handover' : 'Assign'} “{assignCtx.item.name}”</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '0 0 16px' }}>
              {assignCtx.item.asset_code}{assignCtx.item.current_holder ? ` · currently: ${assignCtx.item.current_holder}` : ''}
            </p>
            <div className="fg"><label>{assignCtx.mode === 'handover' ? 'Hand over to' : 'Assign to'} <span className="req">*</span></label>
              <EmployeePicker employees={employees} value={assignForm.assigned_to} onChange={v => setAssignForm({ ...assignForm, assigned_to: v })} />
            </div>
            <div className="fgrid">
              <div className="fg"><label>Date</label><input type="date" value={assignForm.assigned_date} onChange={e => setAssignForm({ ...assignForm, assigned_date: e.target.value })} /></div>
              <div className="fg"><label>Condition on handover</label>
                <select value={assignForm.handover_condition} onChange={e => setAssignForm({ ...assignForm, handover_condition: e.target.value })}>
                  {CONDITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></div>
            </div>
            <div className="fg"><label>Accessories</label><input value={assignForm.accessories} placeholder="Charger, Bag, Mouse" onChange={e => setAssignForm({ ...assignForm, accessories: e.target.value })} /></div>
            <div className="fg"><label>Remarks</label><textarea rows={2} style={{ minHeight: 60 }} value={assignForm.note} onChange={e => setAssignForm({ ...assignForm, note: e.target.value })} /></div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" disabled={saving} onClick={() => setAssignCtx(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={saving || !assignForm.assigned_to} onClick={doAssign}>{saving ? 'Working…' : (assignCtx.mode === 'handover' ? 'Hand Over' : 'Assign')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Return modal */}
      {returnCtx && (
        <div className="modal-overlay" onClick={() => !saving && setReturnCtx(null)}>
          <div className="modal-content" style={{ maxWidth: 460 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 4px', fontSize: 18 }}>Return “{returnCtx.name}”</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '0 0 16px' }}>{returnCtx.asset_code} · from {returnCtx.current_holder || '—'}</p>
            <div className="fg"><label>Return condition</label>
              <select value={returnForm.return_condition} onChange={e => setReturnForm({ ...returnForm, return_condition: e.target.value })}>
                {CONDITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></div>
            <div className="fg"><label>Remarks</label><textarea rows={2} style={{ minHeight: 60 }} value={returnForm.return_remarks} onChange={e => setReturnForm({ ...returnForm, return_remarks: e.target.value })} /></div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" disabled={saving} onClick={() => setReturnCtx(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={saving} onClick={doReturn}>{saving ? 'Returning…' : 'Return to Stock'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InventoryList;
