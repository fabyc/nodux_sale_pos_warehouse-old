# This file is part of the sale_pos module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
#! -*- coding: utf8 -*-
from decimal import Decimal
from trytond.model import ModelView, fields, ModelSQL
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Not
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond import backend

__all__ = ['Sale', 'SaleWarehouse']
__metaclass__ = PoolMeta
_ZERO = Decimal('0.0')

class Sale():
    'Sale'
    __name__ = 'sale.sale'
    warehouse_sale = fields.One2Many('sale.warehouse', 'sale', 'Productos por bodega', readonly=True)
    
    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
            
    @fields.depends('lines', 'currency', 'party', 'self_pick_up', 'warehouse_sale')
    def on_change_lines(self):
        pool = Pool()
        Move = pool.get('stock.product_quantities_warehouse')
        Location = pool.get('stock.location')
        location = Location.search([('type', '=', 'warehouse')])
        Product = Pool().get('product.product')
        Line = pool.get('sale.line')
        line = self.lines
        #todos los movimientos 
        Move = pool.get('stock.move')
        #movimientos de inventario del producto
        StockLine = pool.get('stock.inventory.line')
        stock = 0
        in_s = 0
        res = {}
        if not self.self_pick_up:
            return super(Sale, self).on_change_lines()
        res ['untaxed_amount'] = Decimal('0.0')
        res ['tax_amount']= Decimal('0.0')
        res ['total_amount']=Decimal('0.0')
        res['warehouse_sale'] = {}
        if self.warehouse_sale:
            res['warehouse_sale']['remove'] = [x['id'] for x in self.warehouse_sale]
                    
        if self.lines:
            res['untaxed_amount'] = reduce(lambda x, y: x + y,
                [(getattr(l, 'amount', None) or Decimal(0))
                    for l in self.lines if l.type == 'line'], Decimal(0)
                )
            res['total_amount'] = reduce(lambda x, y: x + y,
                [(getattr(l, 'amount_w_tax', None) or Decimal(0))
                    for l in self.lines if l.type == 'line'], Decimal(0)
                )
            
            tam = len(location)
            for l in self.lines:
                if self.warehouse_sale:
                    res['warehouse_sale']['remove'] = [x['id'] for x in self.warehouse_sale]
                c_location = 1       
                if l.product != None:
                    if self.warehouse_sale:
                        res['warehouse_sale']['remove'] = [x['id'] for x in self.warehouse_sale]
                    for lo in location:
                        #inventario por cada uno de los productos
                        in_stock = Move.search([('product', '=', l.product), ('to_location','=', lo.storage_location)])
                        for i in in_stock :
                            in_s += i.quantity
                        #todos los movimientos que ha tenido el producto
                        move = Move.search([('product', '=', l.product), ('from_location','=', lo.storage_location)])
                        for m in move :
                            stock += m.quantity
                        s_total = in_s - stock
                        if s_total > 0 and c_location == tam:
                            result = {
                                'product': l.product.name,
                                'warehouse': lo.name,
                                'quantity': str(s_total),
                                }
                        elif s_total > 0 and c_location != tam:
                            result = {
                                'product': " ",
                                'warehouse': lo.name,
                                'quantity': str(s_total),
                                }
                        elif s_total <= 0 and c_location != tam:
                            result = {
                                'product': " ",
                                'warehouse': lo.name,
                                'quantity': str(s_total),
                                }
                        elif s_total <= 0 and c_location == tam:
                            result = {
                                'product': l.product.name,
                                'warehouse': lo.name,
                                'quantity': str(s_total),
                                }
                        c_location += 1 
                                
                        stock = 0
                        in_s = 0
                        res['warehouse_sale'].setdefault('add', []).append((0, result))
        if self.currency:
            res['untaxed_amount'] = self.currency.round(res['untaxed_amount'])
            res['total_amount'] = self.currency.round(res['total_amount'])
        res['tax_amount'] = res['total_amount'] - res['untaxed_amount']
        if self.currency:
            res['tax_amount'] = self.currency.round(res['tax_amount'])
            
        return res
    
        
class SaleWarehouse(ModelSQL, ModelView):
    'Producto por Bodega'
    __name__ = 'sale.warehouse'
    
    sale = fields.Many2One('sale.sale', 'Sale', readonly = True)
    product = fields.Char('Producto',  readonly = True)
    warehouse = fields.Char('Bodega',  readonly = True)
    quantity = fields.Char('Cantidad',  readonly = True)
    
