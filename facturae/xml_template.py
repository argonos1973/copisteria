#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo que contiene la plantilla XML para la generación de facturas electrónicas.
"""

import logging

logger = logging.getLogger(__name__)

def obtener_plantilla_xml():
    """
    Devuelve la plantilla base XML para Facturae
    
    Returns:
        str: Plantilla XML base para Facturae
    """
    # Plantilla básica de Facturae 3.2.2 para VERI*FACTU
    return """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml" 
             xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
    <FileHeader>
        <SchemaVersion>3.2.2</SchemaVersion>
        <Modality>I</Modality>
        <InvoiceIssuerType>EM</InvoiceIssuerType>
        <Batch>
            <BatchIdentifier>{batch_id}</BatchIdentifier>
            <InvoicesCount>1</InvoicesCount>
            <TotalInvoicesAmount>
                <TotalAmount>{total_amount}</TotalAmount>
            </TotalInvoicesAmount>
            <TotalOutstandingAmount>
                <TotalAmount>{total_amount}</TotalAmount>
            </TotalOutstandingAmount>
            <TotalExecutableAmount>
                <TotalAmount>{total_amount}</TotalAmount>
            </TotalExecutableAmount>
            <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
        </Batch>
    </FileHeader>
    <Parties>
        <SellerParty>
            {seller_party}
        </SellerParty>
        <BuyerParty>
            {buyer_party}
        </BuyerParty>
    </Parties>
    <Invoices>
        <Invoice>
            <InvoiceHeader>
                <InvoiceNumber>{invoice_number}</InvoiceNumber>
                <InvoiceSeriesCode>{invoice_series}</InvoiceSeriesCode>
                <InvoiceDocumentType>FC</InvoiceDocumentType>
                <InvoiceClass>OO</InvoiceClass>
            </InvoiceHeader>
            <InvoiceIssueData>
                <IssueDate>{issue_date}</IssueDate>
                <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
                <TaxCurrencyCode>EUR</TaxCurrencyCode>
                <LanguageName>es</LanguageName>
            </InvoiceIssueData>
            <TaxesOutputs>
                {taxes_outputs}
            </TaxesOutputs>
            <InvoiceTotals>
                <TotalGrossAmount>{total_gross}</TotalGrossAmount>
                <TotalGrossAmountBeforeTaxes>{total_gross}</TotalGrossAmountBeforeTaxes>
                <TotalTaxOutputs>{total_tax}</TotalTaxOutputs>
                <TotalTaxesWithheld>0.00</TotalTaxesWithheld>
                <InvoiceTotal>{total_amount}</InvoiceTotal>
                <TotalOutstandingAmount>{total_amount}</TotalOutstandingAmount>
                <TotalExecutableAmount>{total_amount}</TotalExecutableAmount>
            </InvoiceTotals>
            <Items>
                {items}
            </Items>
        </Invoice>
    </Invoices>
</fe:Facturae>
"""

def generar_party_template(tipo='seller'):
    """
    Genera la plantilla para un party (vendedor o comprador)
    
    Args:
        tipo (str): 'seller' para vendedor, 'buyer' para comprador
        
    Returns:
        str: Plantilla XML para el party
    """
    if tipo == 'seller':
        return """<TaxIdentification>
                <PersonTypeCode>{person_type_code}</PersonTypeCode>
                <ResidenceTypeCode>R</ResidenceTypeCode>
                <TaxIdentificationNumber>{tax_number}</TaxIdentificationNumber>
            </TaxIdentification>
            <LegalEntity>
                <CorporateName>{corporate_name}</CorporateName>
                <AddressInSpain>
                    <Address>{address}</Address>
                    <PostCode>{post_code}</PostCode>
                    <Town>{town}</Town>
                    <Province>{province}</Province>
                    <CountryCode>ESP</CountryCode>
                </AddressInSpain>
            </LegalEntity>"""
    else:
        return """<TaxIdentification>
                <PersonTypeCode>{person_type_code}</PersonTypeCode>
                <ResidenceTypeCode>R</ResidenceTypeCode>
                <TaxIdentificationNumber>{tax_number}</TaxIdentificationNumber>
            </TaxIdentification>
            <LegalEntity>
                <CorporateName>{corporate_name}</CorporateName>
                <AddressInSpain>
                    <Address>{address}</Address>
                    <PostCode>{post_code}</PostCode>
                    <Town>{town}</Town>
                    <Province>{province}</Province>
                    <CountryCode>ESP</CountryCode>
                </AddressInSpain>
            </LegalEntity>"""

def generar_individual_template():
    """
    Genera la plantilla para una persona física
    
    Returns:
        str: Plantilla XML para una persona física
    """
    return """<TaxIdentification>
            <PersonTypeCode>{person_type_code}</PersonTypeCode>
            <ResidenceTypeCode>R</ResidenceTypeCode>
            <TaxIdentificationNumber>{tax_number}</TaxIdentificationNumber>
        </TaxIdentification>
        <Individual>
            <Name>{name}</Name>
            <FirstSurname>{first_surname}</FirstSurname>
            <SecondSurname>{second_surname}</SecondSurname>
            <AddressInSpain>
                <Address>{address}</Address>
                <PostCode>{post_code}</PostCode>
                <Town>{town}</Town>
                <Province>{province}</Province>
                <CountryCode>ESP</CountryCode>
            </AddressInSpain>
        </Individual>"""

def generar_taxes_template():
    """
    Genera la plantilla para los impuestos
    
    Returns:
        str: Plantilla XML para los impuestos
    """
    return """<Tax>
                <TaxTypeCode>01</TaxTypeCode>
                <TaxRate>{tax_rate}</TaxRate>
                <TaxableBase>
                    <TotalAmount>{taxable_base}</TotalAmount>
                </TaxableBase>
                <TaxAmount>
                    <TotalAmount>{tax_amount}</TotalAmount>
                </TaxAmount>
            </Tax>"""

def generar_item_template():
    """
    Genera la plantilla para un ítem (línea de factura)
    
    Returns:
        str: Plantilla XML para un ítem
    """
    return """<InvoiceLine>
                <ItemDescription>{description}</ItemDescription>
                <Quantity>{quantity}</Quantity>
                <UnitPriceWithoutTax>{unit_price}</UnitPriceWithoutTax>
                <TotalCost>{total_cost}</TotalCost>
                <GrossAmount>{gross_amount}</GrossAmount>
                <TaxesOutputs>
                    <Tax>
                        <TaxTypeCode>01</TaxTypeCode>
                        <TaxRate>{tax_rate}</TaxRate>
                        <TaxableBase>
                            <TotalAmount>{taxable_base}</TotalAmount>
                        </TaxableBase>
                        <TaxAmount>
                            <TotalAmount>{tax_amount}</TotalAmount>
                        </TaxAmount>
                    </Tax>
                </TaxesOutputs>
            </InvoiceLine>"""
