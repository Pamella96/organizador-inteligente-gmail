"""
Configuração declarativa dos serviços de e-mail.

Para adicionar um novo serviço, basta acrescentar um dict à lista SERVICES.
Nenhum outro arquivo precisa ser editado.

Campos de cada serviço:
  name             : nome do serviço (usado no label raiz e no CLI --sync-<slug>)
  label_root       : raiz dos labels no Gmail (default: igual a name)
  queries          : lista de queries Gmail para encontrar os e-mails
  official_domains : lista de domínios aceitos como remetente (None = sem filtro)
  categories       : lista de {"name": str, "descricao": str}
                     O Gemini usa as descrições para classificar — seja específico.
  default          : categoria usada quando nenhuma outra se aplica
"""

SERVICES = [
    {
        "name": "Spotify",
        "queries": [
            "from:(@spotify.com)",
            '"Spotify"',
        ],
        "official_domains": ["spotify.com"],
        "categories": [
            {
                "name": "Seguranca",
                "descricao": "Código de verificação de login, acesso não reconhecido, redefinição de senha, autenticação em dois fatores",
            },
            {
                "name": "Promocao",
                "descricao": "Ofertas de plano Premium, desconto, trial gratuito, promoção relâmpago, 'volte para o Premium'",
            },
            {
                "name": "Notificacao",
                "descricao": "Novidades de artistas seguidos, playlists recomendadas, lançamentos de álbuns, eventos e shows",
            },
            {
                "name": "Conta",
                "descricao": "Confirmação de pagamento mensal, fatura, recibo de assinatura, cobrança realizada",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Discord",
        "queries": [
            "from:(@discord.com OR @discordapp.com)",
            '"Discord"',
        ],
        "official_domains": ["discord.com", "discordapp.com"],
        "categories": [
            {
                "name": "Seguranca",
                "descricao": "Login suspeito, verificação de conta, redefinição de senha, acesso de novo dispositivo, código 2FA",
            },
            {
                "name": "Notificacao",
                "descricao": "Menções em canais, mensagens diretas, convites para servidores, alertas de canal",
            },
            {
                "name": "Novidade",
                "descricao": "Atualizações da plataforma, novos recursos, mudança de política, termos de uso, changelog",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Instagram",
        "queries": [
            "from:(instagram.com OR mail.instagram.com OR facebookmail.com OR @meta.com)",
            '"Instagram"',
        ],
        "official_domains": ["instagram.com", "mail.instagram.com", "facebookmail.com", "meta.com"],
        "categories": [
            {
                "name": "Seguranca",
                "descricao": "Código de verificação, login suspeito em novo dispositivo, redefinição de senha, autenticação",
            },
            {
                "name": "Interacoes",
                "descricao": "Curtidas, comentários, novos seguidores, menções em posts ou stories, marcações",
            },
            {
                "name": "Conta",
                "descricao": "Conta profissional ou business, Meta Business Suite, insights, central de contas",
            },
            {
                "name": "Promocoes",
                "descricao": "Anúncios pagos, impulsionamento de publicações, Meta Ads, publicidade",
            },
            {
                "name": "Suporte",
                "descricao": "Denúncias, apelações, violações de política, conteúdo removido, revisão de conta",
            },
        ],
        "default": "Notificacoes",
    },
    {
        "name": "Facebook",
        "queries": [
            "from:(facebookmail.com OR @facebook.com)",
        ],
        "official_domains": ["facebookmail.com", "facebook.com"],
        "categories": [
            {
                "name": "Seguranca",
                "descricao": "Login suspeito, acesso de novo dispositivo, verificação de identidade, redefinição de senha, código 2FA",
            },
            {
                "name": "Notificacoes",
                "descricao": "Curtidas, comentários, mensagens, solicitações de amizade, eventos, grupos, marcações",
            },
            {
                "name": "Conta",
                "descricao": "Configurações de perfil, políticas da comunidade, termos de uso, padrões da comunidade",
            },
            {
                "name": "Promocoes",
                "descricao": "Meta Ads, impulsionamento de publicações, anúncios pagos, publicidade",
            },
            {
                "name": "Suporte",
                "descricao": "Denúncias, apelações de conta, revisão de conteúdo removido, suporte ao usuário",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Claro",
        "queries": [
            "from:(@minhaclaro.com.br OR @clarorecarga.com.br OR @claroclube.com.br OR @claropromo.com.br OR @claro.com.br)",
            '"Claro"',
        ],
        "official_domains": [
            "minhaclaro.com.br", "clarorecarga.com.br",
            "claroclube.com.br", "claropromo.com.br", "claro.com.br",
        ],
        "categories": [
            {
                "name": "Fatura",
                "descricao": "Fatura mensal, boleto, 2ª via, vencimento, aviso de débito automático",
            },
            {
                "name": "Cobranca",
                "descricao": "Cobrança em aberto, pagamento pendente, aviso de inadimplência, corte iminente",
            },
            {
                "name": "Pesquisa",
                "descricao": "Pesquisa de satisfação, avaliação de atendimento, NPS, opinião do cliente",
            },
            {
                "name": "Promocao",
                "descricao": "Ofertas, promoções, clube de vantagens Claro, recarga bônus, desconto em plano",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Vivo",
        "queries": [
            "from:(@vivo.com.br OR @vivofibra.com.br OR @vivoseg.com.br OR @vivopromo.com.br)",
            '"Vivo"',
        ],
        "official_domains": [
            "vivo.com.br", "vivofibra.com.br",
            "vivoseg.com.br", "vivopromo.com.br",
        ],
        "categories": [
            {
                "name": "Fatura",
                "descricao": "Fatura mensal, boleto, 2ª via, vencimento, aviso de débito automático",
            },
            {
                "name": "Cobranca",
                "descricao": "Cobrança em aberto, pagamento pendente, aviso de inadimplência, corte iminente",
            },
            {
                "name": "Pesquisa",
                "descricao": "Pesquisa de satisfação, avaliação de atendimento, NPS, opinião do cliente",
            },
            {
                "name": "Promocao",
                "descricao": "Ofertas, promoções, clube Vivo, recarga bônus, desconto em plano, upgrade",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "KingHost",
        "queries": [
            "from:(@kinghost.com.br OR @kinghost.com)",
            '"KingHost"',
        ],
        "official_domains": ["kinghost.com.br", "kinghost.com"],
        "categories": [
            {
                "name": "Financeiro",
                "descricao": "Fatura, boleto, cobrança, renovação de plano, checkout, confirmação de pagamento",
            },
            {
                "name": "Suporte",
                "descricao": "Ticket de suporte, chamado aberto, incidente, atendimento ao cliente, helpdesk",
            },
            {
                "name": "Seguranca",
                "descricao": "Senha, login, autenticação em dois fatores, acesso suspeito, redefinição de acesso",
            },
            {
                "name": "Dominio",
                "descricao": "Domínio, DNS, nameserver, zona DNS, certificado SSL, WHOIS, transferência de domínio",
            },
            {
                "name": "Promocao",
                "descricao": "Oferta especial, desconto, upgrade de plano, VPS, cloud, cupom",
            },
            {
                "name": "Cancelamento",
                "descricao": "Cancelamento de serviço, reembolso, estorno, devolução",
            },
            {
                "name": "Renovacao",
                "descricao": "Aviso de renovação automática, vencimento próximo, expiração de serviço ou domínio",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "CorePlay",
        "queries": [
            "from:(@lojacoreplay.com OR @coreplay.com.br OR @coreplay.com OR @paghiper.com OR @paghiper.com.br)",
            '"CorePlay"',
            '"PagHiper"',
        ],
        "official_domains": [
            "lojacoreplay.com", "coreplay.com.br", "coreplay.com",
            "paghiper.com", "paghiper.com.br",
        ],
        "categories": [
            {
                "name": "Financeiro",
                "descricao": "Fatura, boleto, cobrança, confirmação de pagamento, quitação",
            },
            {
                "name": "Renovacao",
                "descricao": "Renovação de serviço, reativação, aviso de vencimento, plano ativo",
            },
            {
                "name": "Suspensao",
                "descricao": "Serviço suspenso, conta bloqueada, suspensão por inadimplência",
            },
            {
                "name": "Suporte",
                "descricao": "Ticket de suporte, chamado, problema de acesso, senha, atendimento",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Jobs",
        "queries": [
            "in:inbox (vaga OR vagas OR emprego OR entrevista OR recrutamento OR candidatura OR applied OR application OR assessment OR career)",
            "in:inbox from:(linkedin.com OR greenhouse.io OR lever.co OR workday.com OR indeed.com OR gupy.io OR infojobs.com)",
        ],
        "official_domains": None,  # e-mails de recrutamento vêm de domínios variados
        "categories": [
            {
                "name": "Aplicadas",
                "descricao": "Confirmação de candidatura recebida, agradecimento por aplicar para a vaga",
            },
            {
                "name": "Entrevistas",
                "descricao": "Convite para entrevista, agendamento de call ou phone screen, video interview",
            },
            {
                "name": "Testes",
                "descricao": "Teste técnico, assessment, desafio de código, case, take-home assignment",
            },
            {
                "name": "Retorno",
                "descricao": "Follow-up do recrutador, próximos passos, feedback sobre a candidatura",
            },
            {
                "name": "Rejeicoes",
                "descricao": "Candidatura não avançou, rejeição, 'não seguiremos com sua candidatura', infelizmente",
            },
            {
                "name": "Alertas",
                "descricao": "Alerta de novas vagas, oportunidades recomendadas, job alerts automáticos",
            },
        ],
        "default": "Indefinido",
    },
    {
        "name": "AliExpress",
        "label_root": "Compras/AliExpress",
        "queries": [
            "from:(aliexpress.com OR @aliexpress.com OR @aliexpress.us OR aliexpress.service@gmail.com)",
            '"AliExpress"',
            '"Aliexpress"',
        ],
        "official_domains": ["aliexpress.com", "aliexpress.us"],
        "categories": [
            {
                "name": "Pedido",
                "descricao": "Confirmação de pedido, pedido recebido, aguardando confirmação do vendedor",
            },
            {
                "name": "Pagamento",
                "descricao": "Confirmação de pagamento, aguardando pagamento, comprovante de transação",
            },
            {
                "name": "Entrega",
                "descricao": "Pedido enviado, em trânsito, saiu do armazém, disponível para retirada, código de rastreamento",
            },
            {
                "name": "Avaliacao",
                "descricao": "Solicitação de avaliação do produto, review, 'sua opinião importa', rate your purchase",
            },
            {
                "name": "PosCompra",
                "descricao": "Cancelamento, reembolso, devolução, disputa aberta, proteção ao comprador, pedido fechado",
            },
            {
                "name": "Promocao",
                "descricao": "Cupom de desconto, oferta especial, sale, promoção relâmpago, 11.11, Black Friday",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Mercado Livre",
        "label_root": "Compras/Mercado Livre",
        "queries": [
            "from:(@mercadolivre.com OR @mercadolibre.com OR @mercadopago.com OR @mercadopago.com.br OR @meli.com)",
            "from:(info@mercadopago.com OR nao-responder@mercadolivre.com OR noreply@mercadolivre.com)",
        ],
        "official_domains": [
            "mercadolivre.com", "mercadolibre.com",
            "mercadopago.com", "mercadopago.com.br", "meli.com",
        ],
        "categories": [
            {
                "name": "Pagamento",
                "descricao": "Pagamento aprovado, PIX, transferência, fatura Mercado Pago, solicitação de dinheiro",
            },
            {
                "name": "Compra",
                "descricao": "Confirmação de compra, pedido realizado, venda confirmada, assinatura renovada",
            },
            {
                "name": "Entrega",
                "descricao": "Produto enviado, em trânsito, código de rastreamento, chegou ao destino, a caminho",
            },
            {
                "name": "Seguranca",
                "descricao": "Alerta de segurança, acesso de novo navegador, login suspeito, verificação de identidade",
            },
            {
                "name": "Promocao",
                "descricao": "Oferta, promoção, desconto, cupom, upgrade de plano, Meli+",
            },
        ],
        "default": "Geral",
    },
    {
        "name": "Amil",
        "queries": [
            "from:(@amil.com.br)",
            '"Amil"',
        ],
        "official_domains": ["amil.com.br"],
        "categories": [
            {
                "name": "Financeiro",
                "descricao": "Fatura, boleto, mensalidade do plano de saúde, cobrança, confirmação de pagamento",
            },
            {
                "name": "Carteirinha",
                "descricao": "Carteirinha do plano, atualização de beneficiário, dados cadastrais, número de matrícula",
            },
            {
                "name": "Atendimento",
                "descricao": "Agendamento de consulta, autorização de exame ou procedimento, guia médica, reembolso de consulta",
            },
            {
                "name": "Promocao",
                "descricao": "Campanha de saúde, benefício especial, desconto em parceiros, oferta para beneficiários",
            },
            {
                "name": "Comunicado",
                "descricao": "Informativo institucional, aviso importante, comunicado geral, mudança de regras do plano",
            },
        ],
        "default": "Geral",
    },
]
